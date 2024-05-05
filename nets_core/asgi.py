"""
ASGI config for nets_core project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from nets_core.middleware.auth_token import AuthTokenMiddleware
from channels.routing import ProtocolTypeRouter, URLRouter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nets_core.settings')

django_asgi_application = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_application,
    #"websocket": AuthTokenMiddleware(
        # URLRouter(
            # Just like the Django URL router, but for WebSockets
            # "nets_core.routing.websocket_urlpatterns"
    #   )
    # ),
})
