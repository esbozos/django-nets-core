from django.conf import settings
from django.http import JsonResponse

from nets_core.decorators import request_handler
from nets_core.routing import build_openapi_paths


DEFAULT_OPENAPI_MODULES = (
    "nets_core.google_auth",
    "nets_core.social_auth",
    "nets_core.views",
)


def build_nets_core_openapi_schema():
    modules = getattr(settings, "NETS_CORE_OPENAPI_MODULES", DEFAULT_OPENAPI_MODULES)
    title = getattr(settings, "NETS_CORE_OPENAPI_TITLE", "NETS CORE API")
    version = getattr(settings, "NETS_CORE_OPENAPI_VERSION", "1.0.0")
    description = getattr(
        settings,
        "NETS_CORE_OPENAPI_DESCRIPTION",
        "Auto-generated OpenAPI schema from request_handler route metadata.",
    )
    tags = getattr(settings, "NETS_CORE_OPENAPI_TAGS", ["nets_core_auth"])

    return {
        "openapi": "3.0.3",
        "info": {
            "title": title,
            "version": version,
            "description": description,
        },
        "paths": build_openapi_paths(*modules, tags=tags),
    }


@request_handler(public=True, path="openapi.json", name="openapi_schema", method="GET")
def openapi_schema(request):
    return JsonResponse(build_nets_core_openapi_schema())
