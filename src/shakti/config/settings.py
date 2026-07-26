"""Layered configuration.

Lookup order (highest priority first):

1. ``os.environ`` (dotted keys map to ``UPPER__CASE``: ``db.url`` -> ``DB__URL``)
2. the ``.env`` file
3. ``config/settings.<profile>.yaml``
4. ``config/settings.yaml``
5. constructor ``defaults``

String values support ``${ENV_VAR}`` / ``${ENV_VAR:default}`` interpolation.
"""

from __future__ import annotations

import copy
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from shakti.config.env import interpolate, parse_env_file
from shakti.config.secrets import Secret
from shakti.exceptions import ConfigError

_MISSING = object()


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge ``override`` into ``base`` (returns a new dict)."""
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def as_bool(value: Any) -> bool:
    """Cast common truthy/falsy representations to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off", ""}:
            return False
    raise ConfigError(f"Cannot interpret {value!r} as a boolean")


def _walk(data: dict[str, Any], dotted_key: str) -> Any:
    current: Any = data
    for part in dotted_key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return _MISSING
    return current


class Config:
    def __init__(
        self,
        config_dir: str | Path = "config",
        env_file: str | Path | None = ".env",
        *,
        profile: str | None = None,
        defaults: dict[str, Any] | None = None,
    ) -> None:
        self.config_dir = Path(config_dir)
        self.profile = profile or os.environ.get("SHAKTI_ENV", "development")
        self._defaults: dict[str, Any] = copy.deepcopy(defaults or {})
        self._env_file: dict[str, str] = (
            parse_env_file(Path(env_file)) if env_file else {}
        )
        self._data = self._load_yaml()

    def _load_yaml(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        candidates = (
            self.config_dir / "settings.yaml",
            self.config_dir / "settings.yml",
            self.config_dir / f"settings.{self.profile}.yaml",
            self.config_dir / f"settings.{self.profile}.yml",
        )
        for candidate in candidates:
            if not candidate.is_file():
                continue
            loaded = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
            if not isinstance(loaded, dict):
                raise ConfigError(f"{candidate} must contain a top-level mapping")
            data = deep_merge(data, loaded)
        return data

    @staticmethod
    def _env_key(key: str) -> str:
        return key.upper().replace(".", "__").replace("-", "_")

    def _env_lookup(self, name: str) -> str | None:
        if name in os.environ:
            return os.environ[name]
        return self._env_file.get(name)

    def _interpolate_node(self, node: Any) -> Any:
        if isinstance(node, str):
            return interpolate(node, self._env_lookup)
        if isinstance(node, dict):
            return {key: self._interpolate_node(value) for key, value in node.items()}
        if isinstance(node, list):
            return [self._interpolate_node(value) for value in node]
        return node

    def _resolve(self, key: str) -> Any:
        env_value = self._env_lookup(self._env_key(key))
        if env_value is not None:
            return interpolate(env_value, self._env_lookup)
        for source in (self._data, self._defaults):
            node = _walk(source, key)
            if node is not _MISSING:
                return self._interpolate_node(node)
        return _MISSING

    def get(
        self,
        key: str,
        default: Any = None,
        cast: Callable[[Any], Any] | None = None,
    ) -> Any:
        value = self._resolve(key)
        if value is _MISSING:
            return default
        if cast is None or value is None:
            return value
        caster = as_bool if cast is bool else cast
        try:
            return caster(value)
        except ConfigError:
            raise
        except (TypeError, ValueError) as exc:
            raise ConfigError(f"Cannot cast config key {key!r} with {cast!r}") from exc

    def require(self, key: str, cast: Callable[[Any], Any] | None = None) -> Any:
        value = self.get(key, default=_MISSING, cast=cast)
        if value is _MISSING:
            raise ConfigError(f"Missing required configuration key: {key!r}")
        return value

    def secret(self, key: str, default: str | None = None) -> Secret | None:
        """Resolve a secret. Supports Docker-style ``<KEY>_FILE`` indirection."""
        env_key = self._env_key(key)
        file_hint = self._env_lookup(f"{env_key}_FILE")
        if file_hint:
            path = Path(file_hint)
            if not path.is_file():
                raise ConfigError(f"Secret file for {key!r} not found: {path}")
            return Secret(path.read_text(encoding="utf-8").strip())
        value = self._resolve(key)
        if value is _MISSING:
            return Secret(default) if default is not None else None
        return Secret(str(value))

    def as_dict(self) -> dict[str, Any]:
        """The merged YAML+defaults tree (env overrides not included)."""
        return self._interpolate_node(deep_merge(self._defaults, self._data))

    def __contains__(self, key: str) -> bool:
        return self._resolve(key) is not _MISSING

    def __getitem__(self, key: str) -> Any:
        return self.require(key)

    def __repr__(self) -> str:
        return f"Config(profile={self.profile!r}, config_dir={str(self.config_dir)!r})"
