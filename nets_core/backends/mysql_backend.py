import json
import logging
from typing import Optional

from django.db import connections, models

from .base import ToJsonBackend, has_nested_fields, parse_field_spec
from .python_backend import PythonBackend

logger = logging.getLogger(__name__)

_FALLBACK = PythonBackend()


def _build_json_object_expr(fields_str: str) -> str:
    """Build MySQL JSON_OBJECT(...) expression covering flat fields only."""
    specs = parse_field_spec(fields_str)
    pairs: list[str] = []
    for spec in specs:
        if not spec["nested"]:
            pairs.extend([f"'{spec['output_name']}'", f"`t`.`{spec['name']}`"])
    return f"JSON_OBJECT({', '.join(pairs)})" if pairs else "NULL"


class MySQLBackend(ToJsonBackend):
    """
    Optimized backend for MySQL / MariaDB using inline JSON_OBJECT expressions.
    Falls back to PythonBackend for nested FK relations or when JSON functions
    are not available.
    """

    def check(self, using: str = "default") -> bool:
        try:
            with connections[using].cursor() as cursor:
                cursor.execute("SELECT JSON_OBJECT('_probe', 1)")
                return cursor.fetchone() is not None
        except Exception:
            return False

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
                    f"SELECT {expr} FROM `{table}` t WHERE t.`id` = %s",
                    [instance.pk],
                )
                row = cursor.fetchone()
            if not row or row[0] is None:
                return None
            return json.loads(row[0]) if isinstance(row[0], str) else row[0]
        except Exception:
            logger.warning("nets_core MySQLBackend: query failed, falling back to PythonBackend")
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
        placeholders = ", ".join(["%s"] * len(ids))
        try:
            with connections[using].cursor() as cursor:
                cursor.execute(
                    f"SELECT {expr} FROM `{table}` t WHERE t.`id` IN ({placeholders})",
                    ids,
                )
                rows = cursor.fetchall()
            return [
                json.loads(row[0]) if isinstance(row[0], str) else row[0]
                for row in rows
            ]
        except Exception:
            logger.warning("nets_core MySQLBackend: query failed, falling back to PythonBackend")
            return _FALLBACK.queryset_to_json(queryset, fields, using)
