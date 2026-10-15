from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from django.utils.dateparse import parse_datetime


def updated_fields_mode():
    mode = getattr(settings, "NETS_CORE_UPDATED_FIELDS_MODE", "full")
    if mode not in ("full", "last", "off"):
        raise ImproperlyConfigured(
            "NETS_CORE_UPDATED_FIELDS_MODE must be full, last or off"
        )
    return mode


def _older(change, cutoff):
    if not isinstance(change, dict) or not isinstance(change.get("time"), str):
        return False
    try:
        moment = parse_datetime(change["time"])
    except (TypeError, ValueError):
        return False
    return (
        moment is not None
        and timezone.is_aware(moment) == timezone.is_aware(cutoff)
        and moment < cutoff
    )


def prune_history(value, keep_last=1, cutoff=None):
    if value is None:
        return None, 0
    if not isinstance(value, dict) or any(
        not isinstance(history, list) for history in value.values()
    ):
        raise ValueError("updated_fields must be an object of change lists or null")
    result = {}
    removed = 0
    for name, history in value.items():
        boundary = max(0, len(history) - keep_last)
        retained = [
            change
            for index, change in enumerate(history)
            if index >= boundary or (cutoff is not None and not _older(change, cutoff))
        ]
        removed += len(history) - len(retained)
        if retained:
            result[name] = retained
    return result, removed
