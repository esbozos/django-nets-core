from abc import ABC, abstractmethod
from typing import Optional

from django.db import models


def parse_field_spec(fields_str: str) -> list[dict]:
    """
    Parse the nets_core nested field specification format.

    Simple field:
        "id"  ->  {"name": "id", "output_name": "id", "nested": None}

    Nested FK field:
        "profile_id:[auth_user_profile;id;name;last_name]"  ->  {
            "name": "profile_id",
            "output_name": "profile",
            "nested": {"table": "auth_user_profile", "fields": ["id", "name", "last_name"]},
        }
    """
    if not fields_str:
        return []

    # Split by comma but only at depth 0 (ignore commas inside brackets)
    parts: list[str] = []
    depth = 0
    current: list[str] = []

    for ch in fields_str:
        if ch == "[":
            depth += 1
            current.append(ch)
        elif ch == "]":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
        else:
            current.append(ch)

    part = "".join(current).strip()
    if part:
        parts.append(part)

    result: list[dict] = []
    for raw in parts:
        if ":" in raw:
            field_name, spec = raw.split(":", 1)
            field_name = field_name.strip()
            spec = spec.strip().lstrip("[").rstrip("]")
            spec_parts = [s.strip() for s in spec.split(";") if s.strip()]
            table_name = spec_parts[0] if spec_parts else ""
            nested_fields = spec_parts[1:] if len(spec_parts) > 1 else []
            output_name = field_name[:-3] if field_name.endswith("_id") else field_name
            result.append(
                {
                    "name": field_name,
                    "output_name": output_name,
                    "nested": {"table": table_name, "fields": nested_fields},
                }
            )
        else:
            result.append({"name": raw, "output_name": raw, "nested": None})

    return result


def has_nested_fields(fields_str: str) -> bool:
    return any(spec["nested"] for spec in parse_field_spec(fields_str))


class ToJsonBackend(ABC):
    """Abstract interface that all database backends must implement."""

    @abstractmethod
    def model_to_json(
        self,
        instance: models.Model,
        fields: str,
        using: str = "default",
    ) -> Optional[dict]:
        """Serialize a single model instance to a dict/JSON-compatible object."""

    @abstractmethod
    def queryset_to_json(
        self,
        queryset: "models.QuerySet",
        fields: str,
        using: str = "default",
    ) -> Optional[list]:
        """Serialize a queryset to a list of dicts/JSON-compatible objects."""

    def check(self, using: str = "default") -> bool:
        """Return True if this backend is ready for the given DB connection alias."""
        return True
