"""
ASGI config for backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

# First we must set the DJANGO_SETTINGS_MODULE environment variable as soon as possible
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# Then we must setup django before importing models
import django                                                           # noqa
django.setup()

# Now we can import the necessary modules
from channels.auth import AuthMiddlewareStack                           # noqa
from channels.routing import ProtocolTypeRouter, URLRouter              # noqa
from channels.security.websocket import AllowedHostsOriginValidator     # noqa
from django.core.asgi import get_asgi_application                       # noqa
from main.urls import ws_urlpatterns                                    # noqa

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter(ws_urlpatterns))),
})
