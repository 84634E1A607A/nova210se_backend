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

## Details

For detailed actions see the dispatch_action method in the MainWebsocketConsumer class;
For detailed notification actions see the notification.py file.
"""

import json
from typing import Coroutine

from channels.db import database_sync_to_async
from channels.exceptions import DenyConnection
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from main.models import User, AuthUser


class MainWebsocketConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_user: AuthUser | None = None
        self.user: User | None = None
        self.session_key: str | None = None

    def send_ok(self, action: str, data: any, req_id: int) -> Coroutine:
        return self.send_json({"action": action, "ok": True, "data": data, "request_id": req_id})

    def send_error(self, error: str, req_id: int, code: int = 400) -> Coroutine:
        return self.send_json({"action": "error", "ok": False, "code": code, "error": error, "request_id": req_id})

    async def connect(self) -> None:
        """
        Accept the connection and authenticate the user based on session

        If the user is not authenticated, the server will return an error and disconnect the client; otherwise,
        the connection will be accepted (but no response will be sent to the client).
        """

        await self.accept()
        self.auth_user = self.scope["user"]

        # Check if user is authenticated
        if self.auth_user.is_anonymous:
            await self.send_error("User is not authenticated", 0, 403)
            raise DenyConnection

        self.user = await database_sync_to_async(User.objects.get)(auth_user=self.auth_user)
        self.session_key = self.scope["session"].session_key

        from main.ws._notification_channels import setup_new_socket_channel
        await setup_new_socket_channel(self)

    async def disconnect(self, close_code: int) -> None:
        if self.user is not None:
            from main.ws._notification_channels import discard_socket_channel
            await discard_socket_channel(self)

    async def dispatch(self, message):
        """
        Dispatch channel messages

        We use "action" instead of "type" as the key, so that any message with "type" key will be sent to the
        system dispatcher, and any without it will be handled by the notification dispatcher.
        """

        if "type" in message:
            return await super().dispatch(message)

        from main.ws._dispatcher import dispatch_notification
        await dispatch_notification(self, message)

    async def receive(self, text_data: str = None, bytes_data: bytes = None, **kwargs) -> None:
        """
        Override the default receive method to avoid raising exceptions on binary data
        """

        if text_data is None:
            await self.send_error("Invalid packet", 0)
            return

        await self.receive_json(await self.decode_json(text_data), **kwargs)

    @classmethod
    async def decode_json(cls, text_data):
        """
        Override the default JSON decoder to return None if the JSON is invalid (instead of raising an exception)
        """

        try:
            return json.loads(text_data)
        except json.decoder.JSONDecodeError:
            return None

    async def receive_json(self, content: dict, **kwargs) -> None:
        """
        Receive JSON content, validate JSON content and dispatch the action to the corresponding method
        """

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

        if action == "ping":
            """
            Ping request, server will respond with pong. Mainly used for testing.

            Unless the server is severely overloaded, the server will respond with a "pong" notification in no time.
            """

            await self.send_ok("pong", None, req_id)

        elif action == "send_message":
            """
            Send a message to a chat

            Expects data to be a dictionary in the following format: {
                "chat_id": int,
                "content": str,
                [optional] "reply_to": int
            }

            chat_id: The chat id to send the message to
            content: The message content
            reply_to: Optional, the message id to reply to

            If the message is successfully sent, you will receive a "new message" notification (see notification.py)

            You must be a member of the chat to send a message; the content must be a non-empty string.

            If the reply_to field is set, the message will be a reply to the message with the specified id,
            where the replied message must be in the same chat.

            If any error condition is met, the server will send an "error" notification with the error message.
            """

            from main.ws.action import send_message
            await send_message(self, data, req_id)

        elif action == "recall_message":
            """
            Recall a sent message.

            Expects data to be a dictionary in the following format: {
                "message_id": int
            }

            You must be the sender to recall the message.

            If the message is successfully recalled, you will receive a "message recalled" notification;
            otherwise, an "error" notification will be sent.
            """

            from main.ws.action import recall_message
            await recall_message(self, data, req_id)

        elif action == "messages_read":
            """
            Mark all messages of a certain chat as read

            Expects data to be a dictionary in the following format: {
                "chat_id": int
            }

            If the user is in the chat, all messages in the chat will be marked as read and no response will be sent;
            otherwise, an error response will be sent.
            """

            from main.ws.action import mark_chat_messages_read
            await mark_chat_messages_read(self, data, req_id)

        else:
            await self.send_error(f"Unknown action: {action}", req_id)
