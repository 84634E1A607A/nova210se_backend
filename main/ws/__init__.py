"""
# Websocket server for the main app

ws://<host>/ws/ Main websocket interface

Authorization (session cookie) is required to connect to websocket interface,
or the server returns a json response with code 403 and disconnects.

## Client to Server packets:

All client-to-server packet should conform to the following format: {
    "action": "ACTION_NAME",
    "request_id": 0, // Optional, helps to identify response
    "data": any
}

Where "action" helps server to identify the intent of the packet; and data type is interpreted based on action.
If the client anticipates a response, set request_id to a certain random number and server will return
the corresponding response with request_id field set.

If the client sends an invalid packet, the server will return an error packet (format described as follows).

## Server to Client packets:

### Error packets

If a client-side error occurs, the server will return an error packet with the following format: {
    "action": "error",
    "request_id": 0,
    "ok": false,
    "code": 400,
    "error": "ERROR_MESSAGE"
}

Where "action" is set to "error", "ok" is set to false, "code" is currently not defined (400 for most cases),
and "error" is the error message. "request_id" is set to the request_id of the packet that caused the error, or 0
if the request_id is not sent / cannot be determined.

### Notification packets

Notification packets are actively sent to the client to notify the client of certain events. The format is as follows: {
    "action": "ACTION_NAME",
    "request_id": 0,
    "ok": true,
    "data": any
}

## Actions

For detailed actions see the dispatch_action method.
"""

import json
from typing import Coroutine

from channels.db import database_sync_to_async
from channels.exceptions import DenyConnection
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from main.models import User, AuthUser
from main.ws.notification_channels import setup_new_socket_channel, discard_socket_channel


class MainWebsocketConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_user: AuthUser | None = None
        self.user: User | None = None

        # This is a hack to avoid socket being corrupted by JSON decoding error
        if AsyncJsonWebsocketConsumer.decode_json != self.decode_json:
            AsyncJsonWebsocketConsumer.decode_json = self.decode_json

    def send_ok(self, action: str, data: any, req_id: int) -> Coroutine:
        return self.send_json({"action": action, "ok": True, "data": data, "request_id": req_id})

    def send_error(self, error: str, req_id: int, code: int = 400) -> Coroutine:
        return self.send_json({"action": "error", "ok": False, "code": code, "error": error, "request_id": req_id})

    async def connect(self) -> None:
        await self.accept()
        self.auth_user = self.scope["user"]

        # Check if user is authenticated
        if self.auth_user.is_anonymous:
            await self.send_error("User is not authenticated", 0, 403)
            raise DenyConnection

        self.user = await database_sync_to_async(User.objects.get)(auth_user=self.auth_user)

        await setup_new_socket_channel(self, self.user)

    async def disconnect(self, close_code: int) -> None:
        await discard_socket_channel(self, self.user)

    async def dispatch(self, message):
        if "type" in message:
            return await super().dispatch(message)

        from main.ws._dispatcher import dispatch_message
        await dispatch_message(self, message)

    @classmethod
    async def decode_json(cls, text_data):
        try:
            return json.loads(text_data)
        except json.decoder.JSONDecodeError:
            return None

    async def receive_json(self, content: dict, **kwargs) -> None:
        # Validate content
        if content is None:
            await self.send_error("Malformed JSON content", 0)
            return

        if not isinstance(content, dict):
            await self.send_error("Invalid JSON content", 0)
            return

        # Validate request_id
        request_id: int = content.get("request_id", 0)
        if not isinstance(request_id, int):
            await self.send_error("Invalid request_id", 0)
            return

        # Get and validate action
        if "action" not in content:
            await self.send_error("No action specified", 0)
            return

        action: str = content.get("action", "")
        if not isinstance(action, str):
            await self.send_error("Invalid action type", request_id)
            return

        # Dispatch action
        try:
            await self.dispatch_action(action, content.get("data", None), request_id)
        except Exception as e:
            await self.send_error(f"Internal Server Error: {e}", request_id, code=500)

    async def dispatch_action(self, action: str, data: any, req_id: int) -> None:
        """
        Dispatch action to corresponding method
        """

        # Ping request, server will respond with pong. Mainly used for testing
        if action == "ping":
            await self.send_ok("pong", None, req_id)

        else:
            await self.send_error(f"Unknown action: {action}", req_id)
