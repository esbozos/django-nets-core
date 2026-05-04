import logging
from typing import Optional

from django.db import connections, models

from .base import ToJsonBackend
from .python_backend import PythonBackend

logger = logging.getLogger(__name__)

_PROBE_QUERY = (
    "SELECT proname FROM pg_proc WHERE proname = 'nets_core_postgre_model_to_json'"
)


class PostgreSQLBackend(ToJsonBackend):
    """
    Optimized backend using PostgreSQL stored procedures installed by nets_core.
    Automatically falls back to PythonBackend when the procedures are not found
    (e.g. during first migrate before post_migrate installs them).
    """

    def check(self, using: str = "default") -> bool:
        try:
            with connections[using].cursor() as cursor:
                cursor.execute(_PROBE_QUERY)
                return cursor.fetchone() is not None
        except Exception:
            return False

    def _fallback(self) -> PythonBackend:
        return PythonBackend()

    def model_to_json(
        self,
        instance: models.Model,
        fields: str,
        using: str = "default",
    ) -> Optional[dict]:
        if not self.check(using):
            logger.debug(
                "nets_core PostgreSQLBackend: procedure not installed, using PythonBackend"
            )
            return self._fallback().model_to_json(instance, fields, using)

        query = (
            f"SELECT nets_core_postgre_model_to_json"
            f"('{instance._meta.db_table}', '{fields}', {instance.pk})"
        )
        with connections[using].cursor() as cursor:
            cursor.execute(query)
            row = cursor.fetchone()
        return row[0] if row else None

    def queryset_to_json(
        self,
        queryset: "models.QuerySet",
        fields: str,
        using: str = "default",
    ) -> Optional[list]:
        if not self.check(using):
            logger.debug(
                "nets_core PostgreSQLBackend: procedure not installed, using PythonBackend"
            )
            return self._fallback().queryset_to_json(queryset, fields, using)

        ids = ", ".join(str(obj.pk) for obj in queryset)
        query = (
            f"SELECT nets_core_postgre_array_model_to_json"
            f"('{queryset.model._meta.db_table}', '{fields}', ARRAY[{ids}])"
        )
        with connections[using].cursor() as cursor:
            cursor.execute(query)
            row = cursor.fetchone()
        return row[0] if row else None
