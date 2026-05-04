import json
import logging
from typing import Optional

from django.db import connections, models

from .base import ToJsonBackend, has_nested_fields, parse_field_spec
from .python_backend import PythonBackend

logger = logging.getLogger(__name__)

_FALLBACK = PythonBackend()


def _has_json1(using: str = "default") -> bool:
    """Check if SQLite JSON1 extension is available."""
    try:
        with connections[using].cursor() as cursor:
            cursor.execute("SELECT json_object('_probe', 1)")
            return cursor.fetchone() is not None
    except Exception:
        return False


def _build_json_object_expr(fields_str: str) -> str:
    """Build SQLite json_object(...) expression covering flat fields only."""
    specs = parse_field_spec(fields_str)
    pairs: list[str] = []
    for spec in specs:
        if not spec["nested"]:
            pairs.extend([f"'{spec['output_name']}'", f'"t"."{spec["name"]}"'])
    return f"json_object({', '.join(pairs)})" if pairs else "NULL"


class SQLiteBackend(ToJsonBackend):
    """
    Optimized backend for SQLite using the built-in JSON1 extension.
    Falls back to PythonBackend when JSON1 is not available or fields are nested.

    JSON1 is bundled in CPython's sqlite3 since Python 3.x and SQLite ≥ 3.9.
    """

    def check(self, using: str = "default") -> bool:
        return _has_json1(using)

    def model_to_json(
        self,
        instance: models.Model,
        fields: str,
        using: str = "default",
    ) -> Optional[dict]:
        if has_nested_fields(fields) or not self.check(using):
            return _FALLBACK.model_to_json(instance, fields, using)

        expr = _build_json_object_expr(fields)
        table = instance._meta.db_table
        try:
            with connections[using].cursor() as cursor:
                cursor.execute(
                    f'SELECT {expr} FROM "{table}" t WHERE t."id" = ?',
                    [instance.pk],
                )
                row = cursor.fetchone()
            if not row or row[0] is None:
                return None
            return json.loads(row[0]) if isinstance(row[0], str) else row[0]
        except Exception:
            logger.warning("nets_core SQLiteBackend: query failed, falling back to PythonBackend")
            return _FALLBACK.model_to_json(instance, fields, using)

    def queryset_to_json(
        self,
        queryset: "models.QuerySet",
        fields: str,
        using: str = "default",
    ) -> Optional[list]:
        if has_nested_fields(fields) or not self.check(using):
            return _FALLBACK.queryset_to_json(queryset, fields, using)

        expr = _build_json_object_expr(fields)
        table = queryset.model._meta.db_table
        ids = [obj.pk for obj in queryset]
        placeholders = ", ".join(["?"] * len(ids))
        try:
            with connections[using].cursor() as cursor:
                cursor.execute(
                    f'SELECT {expr} FROM "{table}" t WHERE t."id" IN ({placeholders})',
                    ids,
                )
                rows = cursor.fetchall()
            return [
                json.loads(row[0]) if isinstance(row[0], str) else row[0]
                for row in rows
            ]
        except Exception:
            logger.warning("nets_core SQLiteBackend: query failed, falling back to PythonBackend")
            return _FALLBACK.queryset_to_json(queryset, fields, using)
