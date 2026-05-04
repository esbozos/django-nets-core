from importlib import import_module
from types import ModuleType
from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.urls import path


ROUTE_ATTR = "__nets_core_route__"
DEFAULT_OPENAPI_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")


def _resolve_module(module: str | ModuleType) -> ModuleType:
    if isinstance(module, str):
        return import_module(module)
    return module


def _iter_decorated_views(module: ModuleType):
    for value in module.__dict__.values():
        route = getattr(value, ROUTE_ATTR, None)
        if route:
            yield value, route


def _normalize_openapi_path(route_path: str) -> str:
    normalized = route_path if route_path.startswith("/") else f"/{route_path}"
    return normalized or "/"


def _collect_routes(*modules: str | ModuleType):
    routes = []
    seen_paths = set()
    seen_names = set()

    for module_ref in modules:
        module = _resolve_module(module_ref)

        for view, route in _iter_decorated_views(module):
            route_path = route["path"]
            route_name = route["name"]
            route_methods = route.get("methods")

            if route_path in seen_paths:
                raise ImproperlyConfigured(
                    f"Duplicate auto route path detected: '{route_path}'"
                )

            if route_name in seen_names:
                raise ImproperlyConfigured(
                    f"Duplicate auto route name detected: '{route_name}'"
                )

            seen_paths.add(route_path)
            seen_names.add(route_name)
            routes.append(
                {
                    "path": route_path,
                    "name": route_name,
                    "methods": tuple(route_methods) if route_methods else None,
                    "view": view,
                    "module": module.__name__,
                    "view_name": getattr(view, "__name__", str(view)),
                }
            )

    return routes


def build_route_registry(*modules: str | ModuleType):
    """
    Collect declarative routes from decorated views for docs/inspection use cases.
    """
    routes = _collect_routes(*modules)
    return [
        {
            "path": r["path"],
            "name": r["name"],
            "methods": r["methods"],
            "module": r["module"],
            "view_name": r["view_name"],
        }
        for r in routes
    ]


def build_openapi_paths(
    *modules: str | ModuleType,
    tags: list[str] | None = None,
    default_methods: tuple[str, ...] = DEFAULT_OPENAPI_METHODS,
) -> dict[str, dict[str, Any]]:
    """
    Build OpenAPI `paths` object from routes declared with request_handler.
    """
    paths: dict[str, dict[str, Any]] = {}
    tag_values = tags or ["nets_core"]

    for route in _collect_routes(*modules):
        openapi_path = _normalize_openapi_path(route["path"])
        methods = route["methods"] or default_methods
        operation_base = route["name"].replace("-", "_")

        path_item = paths.setdefault(openapi_path, {})
        for http_method in methods:
            method_name = http_method.lower()
            path_item[method_name] = {
                "operationId": f"{operation_base}_{method_name}",
                "tags": tag_values,
                "responses": {
                    "200": {"description": "OK"},
                    "405": {"description": "Method Not Allowed"},
                },
                "x-nets-core-route-name": route["name"],
                "x-nets-core-view": f"{route['module']}.{route['view_name']}",
            }

    return paths


def build_urlpatterns(*modules: str | ModuleType):
    """
    Build django URL patterns from views decorated with request_handler(path=..., name=...).
    """
    return [path(r["path"], r["view"], name=r["name"]) for r in _collect_routes(*modules)]
