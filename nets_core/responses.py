import json
from collections import namedtuple
from typing import NamedTuple

from django.db.models import Model
from django.http import HttpRequest, JsonResponse
from django.utils.translation import gettext_lazy as _


def success_response(data, extra=None):
    """
    Parse list tuple of jsonb from postgresql
    to json response
    """
    if extra:
        return JsonResponse({"res": 1, "data": data, "extra": extra})

    return JsonResponse({"res": 1, "data": data})


def permission_denied():
    return JsonResponse({"res": 0, "message": _("permission denied")}, status=403)


def notfound_response():
    return JsonResponse({"res": 0, "message": _("not found")}, status=404)


def error_response(message: str = None, error: int = 400, data=None):
    return JsonResponse(
        {"res": 0, "message": message if message else _("Bad request"), "data": data},
        status=error,
    )
