from django.db import models, connections
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from nets_core.backends import get_backend

GLOBAL_PROTECTED_FIELDS = [
    "password",
    "superuser",
]

if hasattr(settings, "NETS_CORE_GLOBAL_PROTECTED_FIELDS"):
    GLOBAL_PROTECTED_FIELDS = settings.NETS_CORE_GLOBAL_PROTECTED_FIELDS


def _filter_protected(fields: tuple, model_or_instance) -> tuple:
    """Return a new fields tuple with protected fields removed."""
    if hasattr(model_or_instance, "PROTECTED_FIELDS"):
        protected = {f.lower() for f in model_or_instance.PROTECTED_FIELDS}
        return tuple(f for f in fields if f.lower() not in protected)

    filtered = list(fields)
    for pf in GLOBAL_PROTECTED_FIELDS:
        filtered = [f for f in filtered if pf.lower() not in f.lower()]
    return tuple(filtered)


class NetsCoreQuerySetToJson:

    def __init__(self, queryset: models.QuerySet, fields: tuple = None, using: str = "default"):
        if not fields:
            if hasattr(queryset.model, "JSON_DATA_FIELDS"):
                if not queryset.model.JSON_DATA_FIELDS:
                    raise ValueError(_("Fields must be provided"))
                if not isinstance(queryset.model.JSON_DATA_FIELDS, tuple):
                    try:
                        fields = tuple(queryset.model.JSON_DATA_FIELDS)
                    except Exception:
                        raise ValueError(_("Fields must be a tuple or list"))
            else:
                raise ValueError(_("Fields must be provided"))

        if not isinstance(fields, tuple):
            raise ValueError(_("Fields must be a tuple"))

        if not isinstance(queryset, models.QuerySet):
            raise ValueError(_("Queryset must be a queryset instance or subclass of models.QuerySet"))

        if not isinstance(using, str):
            raise ValueError(_("Using must be a string"))

        if using not in connections.databases:
            raise ValueError(_("Database alias not found"))

        self.queryset = queryset
        first = queryset.first()
        if first is not None:
            fields = _filter_protected(fields, first)

        self.fields = ", ".join(fields)
        self.using = using

    def to_json(self):
        backend = get_backend(self.using)
        return backend.queryset_to_json(self.queryset, self.fields, self.using)


class NetsCoreModelToJson:

    def __init__(self, instance: models.Model, fields: tuple = None, using: str = "default"):
        if not fields:
            if hasattr(instance, "JSON_DATA_FIELDS"):
                if not instance.JSON_DATA_FIELDS:
                    raise ValueError(_("Fields must be provided"))
                if not isinstance(instance.JSON_DATA_FIELDS, tuple):
                    try:
                        fields = tuple(instance.JSON_DATA_FIELDS)
                    except Exception:
                        raise ValueError(_("Fields must be a tuple or list"))
            else:
                raise ValueError(_("Fields must be provided"))

        if not isinstance(fields, tuple):
            raise ValueError(_("Fields must be a tuple"))

        if not isinstance(instance, models.Model):
            raise ValueError(_("Instance must be a model instance or subclass of models.Model"))

        if not isinstance(using, str):
            raise ValueError(_("Using must be a string"))

        if using not in connections.databases:
            raise ValueError(_("Database alias not found"))

        self.instance = instance
        fields = _filter_protected(fields, instance)
        self.fields = ",".join(fields)
        self.using = using

    def to_json(self, returning_query: bool = False):
        if returning_query:
            # Kept for backward-compatible debug/inspection use (PostgreSQL-specific format)
            return (
                f"SELECT nets_core_postgre_model_to_json"
                f"('{self.instance._meta.db_table}', '{self.fields}', {self.instance.pk})"
            )
        backend = get_backend(self.using)
        return backend.model_to_json(self.instance, self.fields, self.using)

