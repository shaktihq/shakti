"""OpenAPI 3.0 spec generation + Swagger UI + ReDoc.

Usage::

    from shakti.openapi import OpenAPI

    openapi = OpenAPI(app, title="My API", version="1.0.0")
    openapi.init_app(app)

    # Visit:
    # http://localhost:8000/docs      → Swagger UI
    # http://localhost:8000/redoc     → ReDoc
    # http://localhost:8000/openapi.json → Raw JSON spec
"""

from __future__ import annotations

import inspect
import re
from typing import Any, get_type_hints

from shakti.http.response import HTMLResponse
from shakti.routing.router import Router

_PY_TO_OPENAPI: dict[str, dict] = {
    "str":      {"type": "string"},
    "int":      {"type": "integer"},
    "float":    {"type": "number"},
    "bool":     {"type": "boolean"},
    "list":     {"type": "array", "items": {}},
    "dict":     {"type": "object"},
    "bytes":    {"type": "string", "format": "binary"},
    "datetime": {"type": "string", "format": "date-time"},
    "None":     {},
}


def _type_schema(annotation: Any) -> dict:
    name = getattr(annotation, "__name__", str(annotation))
    return _PY_TO_OPENAPI.get(name, {"type": "string"})


def _path_to_openapi(path: str) -> str:
    """Convert {id:int} → {id}."""
    return re.sub(r"\{(\w+):[^}]+\}", r"{\1}", path)


def _extract_path_params(path: str) -> list[dict]:
    params = []
    for match in re.finditer(r"\{(\w+)(?::(\w+))?\}", path):
        name = match.group(1)
        type_name = match.group(2) or "str"
        schema = _PY_TO_OPENAPI.get(type_name, {"type": "string"})
        params.append({
            "name": name,
            "in": "path",
            "required": True,
            "schema": schema,
        })
    return params


def generate_spec(app: Any, title: str, version: str, description: str = "") -> dict:
    """Generate an OpenAPI 3.0 specification from app routes."""
    paths: dict[str, Any] = {}

    for route in app.router.routes:
        openapi_path = _path_to_openapi(route.path)
        if openapi_path not in paths:
            paths[openapi_path] = {}

        try:
            hints = get_type_hints(route.endpoint)
        except Exception:
            hints = {}

        return_hint = hints.pop("return", None)
        response_schema = _type_schema(return_hint) if return_hint else {}

        # Extract query params (non-path, non-special params)
        path_param_names = {m.group(1) for m in re.finditer(r"\{(\w+)", route.path)}
        sig = inspect.signature(route.endpoint)
        query_params = []
        for pname, param in sig.parameters.items():
            if pname in ("request", "body", "self") or pname in path_param_names:
                continue
            annotation = hints.get(pname, str)
            schema = _type_schema(annotation)
            required = param.default is inspect.Parameter.empty
            query_params.append({
                "name": pname,
                "in": "query",
                "required": required,
                "schema": schema,
            })

        path_params = _extract_path_params(route.path)
        all_params = path_params + query_params

        doc = (route.endpoint.__doc__ or "").strip()
        summary = doc.split("\n")[0] if doc else route.endpoint.__name__.replace("_", " ").title()

        for method in sorted(route.methods - {"HEAD"}):
            operation: dict[str, Any] = {
                "summary": summary,
                "operationId": f"{method.lower()}_{route.endpoint.__name__}",
                "tags": [openapi_path.split("/")[1] or "root"],
                "parameters": all_params,
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": response_schema if response_schema else {"type": "object"}
                            }
                        }
                    },
                    "422": {"description": "Validation Error"},
                },
            }

            if method in ("POST", "PUT", "PATCH"):
                operation["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"}
                        }
                    },
                }

            paths[openapi_path][method.lower()] = operation

    return {
        "openapi": "3.0.0",
        "info": {
            "title": title,
            "version": version,
            "description": description,
        },
        "paths": paths,
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            }
        },
    }


_SWAGGER_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>{title} — Swagger UI</title>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>
  SwaggerUIBundle({{
    url: "{openapi_url}",
    dom_id: '#swagger-ui',
    presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
    layout: "BaseLayout",
    deepLinking: true,
    showExtensions: true,
    showCommonExtensions: true
  }})
</script>
</body>
</html>"""

_REDOC_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>{title} — ReDoc</title>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
  <style>body{{margin:0;padding:0}}</style>
</head>
<body>
  <redoc spec-url="{openapi_url}"></redoc>
  <script src="https://cdn.jsdelivr.net/npm/redoc@latest/bundles/redoc.standalone.js"></script>
</body>
</html>"""


class OpenAPI:
    """Auto-generate OpenAPI docs + Swagger UI + ReDoc.

    Usage::

        from shakti.openapi import OpenAPI

        openapi = OpenAPI(app, title="My API", version="1.0.0")
        openapi.init_app(app)
    """

    def __init__(
        self,
        app: Any,
        *,
        title: str | None = None,
        version: str = "1.0.0",
        description: str = "",
        docs_url: str = "/docs",
        redoc_url: str = "/redoc",
        openapi_url: str = "/openapi.json",
    ) -> None:
        self._app = app
        self.title = title or getattr(app, "title", "Shakti API")
        self.version = version
        self.description = description
        self.docs_url = docs_url
        self.redoc_url = redoc_url
        self.openapi_url = openapi_url

    def init_app(self, app: Any) -> None:
        _oa = self
        router = Router()

        @router.get(self.openapi_url)
        async def openapi_spec() -> dict:
            return generate_spec(_oa._app, _oa.title, _oa.version, _oa.description)

        @router.get(self.docs_url)
        async def swagger_ui() -> HTMLResponse:
            return HTMLResponse(
                _SWAGGER_HTML.format(title=_oa.title, openapi_url=_oa.openapi_url)
            )

        @router.get(self.redoc_url)
        async def redoc() -> HTMLResponse:
            return HTMLResponse(
                _REDOC_HTML.format(title=_oa.title, openapi_url=_oa.openapi_url)
            )

        app.include_router(router)

    def __repr__(self) -> str:
        return f"<OpenAPI title={self.title!r} docs={self.docs_url!r}>"
