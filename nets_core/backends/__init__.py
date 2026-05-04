"""
nets_core backend selector.

Backends are chosen based on the DB engine (``connection.vendor``) and the
optional ``NETS_CORE_TO_JSON_BACKEND`` setting:

  "auto"   (default) — use the optimized vendor backend; fall back to Python
                       if the backend is unavailable or its check() fails.
  "python"           — always use PythonBackend (portable, no DB-level functions).
  "sql"              — use the vendor-specific SQL backend; raise if unavailable.

Custom backends are supported by setting ``NETS_CORE_TO_JSON_BACKEND`` to a
dotted import path: e.g. ``"myapp.backends.CustomBackend"``.
"""

import importlib
import logging

from django.conf import settings
from django.db import connections

from .base import ToJsonBackend
from .python_backend import PythonBackend

logger = logging.getLogger(__name__)

_PYTHON_BACKEND = PythonBackend()

# Vendor → dotted-path of the optimized backend class
_VENDOR_MAP: dict[str, str] = {
    "postgresql": "nets_core.backends.postgresql_backend.PostgreSQLBackend",
    "mysql": "nets_core.backends.mysql_backend.MySQLBackend",
    "sqlite": "nets_core.backends.sqlite_backend.SQLiteBackend",
}


def _import_class(dotted: str) -> type:
    module_path, class_name = dotted.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def get_backend(using: str = "default") -> ToJsonBackend:
    """
    Return the appropriate ToJsonBackend for the given DB connection alias.
    """
    raw_setting = getattr(settings, "NETS_CORE_TO_JSON_BACKEND", "auto")
    mode = raw_setting.lower() if raw_setting.lower() in ("auto", "python", "sql") else "custom"

    # Explicit Python mode
    if mode == "python":
        return _PYTHON_BACKEND

    # Custom dotted-path backend
    if mode == "custom":
        try:
            BackendClass = _import_class(raw_setting)
            return BackendClass()
        except Exception as exc:
            raise RuntimeError(
                f"nets_core: failed to load custom backend '{raw_setting}': {exc}"
            ) from exc

    # auto / sql
    vendor = connections[using].vendor
    dotted = _VENDOR_MAP.get(vendor)

    if not dotted:
        if mode == "sql":
            raise RuntimeError(
                f"nets_core: no SQL backend available for DB engine '{vendor}'. "
                "Use NETS_CORE_TO_JSON_BACKEND = 'python' or provide a custom backend."
            )
        return _PYTHON_BACKEND

    try:
        BackendClass = _import_class(dotted)
        backend = BackendClass()
    except Exception as exc:
        if mode == "sql":
            raise RuntimeError(
                f"nets_core: failed to load SQL backend for '{vendor}': {exc}"
            ) from exc
        logger.warning(
            "nets_core: failed to import backend for '%s': %s — using PythonBackend",
            vendor,
            exc,
        )
        return _PYTHON_BACKEND

    if not backend.check(using):
        if mode == "sql":
            raise RuntimeError(
                f"nets_core: SQL backend for '{vendor}' is not ready on connection '{using}'."
            )
        logger.debug(
            "nets_core: backend for '%s' check() failed — using PythonBackend",
            vendor,
        )
        return _PYTHON_BACKEND

    return backend


__all__ = ["get_backend", "ToJsonBackend", "PythonBackend"]
