import logging
import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Optional

from django.apps import apps
from django.db import models

from .base import ToJsonBackend, parse_field_spec

logger = logging.getLogger(__name__)

_MAX_DEPTH = 5


def _resolve_value(raw: Any) -> Any:
    """Convert non-serializable Django field values to JSON-safe primitives."""
    if isinstance(raw, (str, int, float, bool, type(None))):
        return raw
    if isinstance(raw, Decimal):
        return float(raw)
    if isinstance(raw, datetime):
        return raw.isoformat()
    if isinstance(raw, date):
        return raw.isoformat()
    if isinstance(raw, time):
        return raw.isoformat()
    if isinstance(raw, uuid.UUID):
        return str(raw)
    if isinstance(raw, (list, tuple)):
        return [_resolve_value(v) for v in raw]
    if isinstance(raw, dict):
        return {k: _resolve_value(v) for k, v in raw.items()}
    return str(raw)


def _model_by_table(table_name: str) -> Optional[type]:
    for model in apps.get_models():
        if model._meta.db_table == table_name:
            return model
    return None


def _serialize_instance(instance: models.Model, fields_str: str, depth: int = 0) -> Optional[dict]:
    if depth > _MAX_DEPTH:
        logger.warning("nets_core PythonBackend: max nesting depth reached, returning None")
        return None

    specs = parse_field_spec(fields_str)
    result: dict = {}

    for spec in specs:
        field_name = spec["name"]
        output_name = spec["output_name"]

        if spec["nested"]:
            nested_info = spec["nested"]
            nested_table = nested_info["table"]
            nested_field_names = nested_info["fields"]

            fk_value = getattr(instance, field_name, None)
            if fk_value is None:
                result[output_name] = None
                continue

            related_model = _model_by_table(nested_table)
            if related_model is None:
                logger.warning(
                    "nets_core PythonBackend: no Django model found for table '%s'",
                    nested_table,
                )
                result[output_name] = None
                continue

            try:
                related_instance = related_model._default_manager.get(pk=fk_value)
                result[output_name] = _serialize_instance(
                    related_instance,
                    ",".join(nested_field_names),
                    depth=depth + 1,
                )
            except related_model.DoesNotExist:
                result[output_name] = None
        else:
            result[output_name] = _resolve_value(getattr(instance, field_name, None))

    return result


class PythonBackend(ToJsonBackend):
    """
    Universal backend using Django ORM attribute access.
    Works on all database engines without any SQL functions or extensions.
    Supports nested FK relations.
    """

    def model_to_json(
        self,
        instance: models.Model,
        fields: str,
        using: str = "default",
    ) -> Optional[dict]:
        return _serialize_instance(instance, fields)

    def queryset_to_json(
        self,
        queryset: "models.QuerySet",
        fields: str,
        using: str = "default",
    ) -> Optional[list]:
        return [_serialize_instance(obj, fields) for obj in queryset]
