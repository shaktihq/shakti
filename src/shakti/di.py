"""Dependency injection: service container + handler parameter binding.

Binding order for each handler parameter:

1. ``Depends(...)`` default          -> resolved (request-scoped cache)
2. annotation is ``Request``         -> the current request
3. name found in path params         -> converted to the annotated type
4. annotation registered in container -> container-resolved service
5. name == ``body``                  -> parsed JSON request body
6. name found in query params        -> converted to the annotated type
7. parameter default                 -> used as-is
8. otherwise                         -> 422 Unprocessable Entity
"""

from __future__ import annotations

import inspect
import typing
from collections.abc import Callable
from typing import Any

from shakti.exceptions import HTTPException
from shakti.http.request import Request

_EMPTY = inspect.Parameter.empty


class Depends:
    """Marker used as a parameter default to declare a dependency."""

    __slots__ = ("dependency", "use_cache")

    def __init__(self, dependency: Callable[..., Any], *, use_cache: bool = True) -> None:
        if not callable(dependency):
            raise TypeError("Depends(...) requires a callable")
        self.dependency = dependency
        self.use_cache = use_cache

    def __repr__(self) -> str:
        name = getattr(self.dependency, "__name__", repr(self.dependency))
        return f"Depends({name})"


class Container:
    """A minimal service container supporting singletons and factories."""

    def __init__(self) -> None:
        self._factories: dict[Any, tuple[Callable[[], Any], bool]] = {}
        self._instances: dict[Any, Any] = {}

    def register_instance(self, key: Any, instance: Any) -> None:
        self._instances[key] = instance

    def register(
        self,
        key: Any,
        factory: Callable[[], Any] | None = None,
        *,
        singleton: bool = True,
    ) -> None:
        if factory is None:
            if not callable(key):
                raise TypeError(
                    "register(key) without a factory requires key to be callable"
                )
            factory = key
        self._factories[key] = (factory, singleton)

    def has(self, key: Any) -> bool:
        try:
            return key in self._instances or key in self._factories
        except TypeError:
            return False

    def resolve(self, key: Any) -> Any:
        if key in self._instances:
            return self._instances[key]
        if key in self._factories:
            factory, singleton = self._factories[key]
            value = factory()
            if singleton:
                self._instances[key] = value
            return value
        raise LookupError(f"No provider registered for {key!r}")


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _convert_value(raw: Any, annotation: Any, name: str, source: str) -> Any:
    if annotation is _EMPTY or annotation is Any or annotation is str:
        return raw
    if not isinstance(annotation, type):
        return raw
    if annotation is not bool and isinstance(raw, annotation):
        return raw
    if annotation is bool:
        lowered = str(raw).strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
        raise HTTPException(422, f"Invalid boolean for {source} parameter {name!r}")
    try:
        return annotation(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, f"Invalid value for {source} parameter {name!r}") from exc


async def build_kwargs(
    func: Callable[..., Any], request: Request, container: Container
) -> dict[str, Any]:
    signature = inspect.signature(func)
    try:
        hints = typing.get_type_hints(func)
    except Exception:
        hints = {}

    kwargs: dict[str, Any] = {}
    for name, parameter in signature.parameters.items():
        if parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
            continue
        annotation = hints.get(name, parameter.annotation)

        if isinstance(parameter.default, Depends):
            kwargs[name] = await _resolve_depends(parameter.default, request, container)
            continue
        if annotation is Request or (annotation is _EMPTY and name == "request"):
            kwargs[name] = request
            continue
        if name in request.path_params:
            kwargs[name] = _convert_value(request.path_params[name], annotation, name, "path")
            continue
        if container.has(annotation):
            kwargs[name] = container.resolve(annotation)
            continue
        if name == "body":
            kwargs[name] = await request.json()
            continue
        if name in request.query_params:
            kwargs[name] = _convert_value(
                request.query_params.get(name), annotation, name, "query"
            )
            continue
        if parameter.default is not _EMPTY:
            kwargs[name] = parameter.default
            continue
        raise HTTPException(422, f"Missing required parameter {name!r}")
    return kwargs


async def _resolve_depends(dep: Depends, request: Request, container: Container) -> Any:
    cache = request._depends_cache
    if dep.use_cache and dep.dependency in cache:
        return cache[dep.dependency]
    value = await call_with_injection(dep.dependency, request, container)
    if dep.use_cache:
        cache[dep.dependency] = value
    return value


async def call_with_injection(
    func: Callable[..., Any], request: Request, container: Container
) -> Any:
    import inspect
    kwargs = await build_kwargs(func, request, container)
    result = func(**kwargs)
    if inspect.isasyncgen(result):
        return await result.__anext__()
    return await _maybe_await(result)
