from django.urls import path
from main.ws import MainWebsocketConsumer

ws_urlpatterns = [
    path('ws/', MainWebsocketConsumer.as_asgi(), name='main_websocket'),
]
