"""
Unit tests for main websocket
"""
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from channels.testing import WebsocketCommunicator
from django.urls import reverse

from main.tests.utils import JsonClient, create_user, get_user_by_name, logout_user, create_friendship, login_user
from main.ws import MainWebsocketConsumer
from main.models import Chat, ChatMessage, User


class TestWebsocket(TestCase):
    async def setup(self):
        self.client = JsonClient()
        self.communicator = WebsocketCommunicator(MainWebsocketConsumer.as_asgi(), "/ws/")

        def setup_sync():
            self.assertTrue(create_user(self.client, "main"))
            self.user = get_user_by_name("main")

            # Patch websocket consumer to add user and session scope
            self.communicator.scope["user"] = self.user.auth_user
            self.communicator.scope["session"] = self.client.session

        await database_sync_to_async(setup_sync)()

    async def test_websocket_connection(self):
        """
        Make sure that after patching, the websocket connection works
        """

        await self.setup()
        connected, _ = await self.communicator.connect()
        self.assertTrue(connected)

        await self.communicator.send_json_to({"action": "ping"})
        response = await self.communicator.receive_json_from()
        self.assertTrue(response["ok"])
        self.assertEqual(response["action"], "pong")

    async def test_websocket_connection_unauthenticated(self):
        """
        Test that authentication is required and working
        """

        await self.setup()

        def logout_sync():
            self.assertTrue(logout_user(self.client))
            self.communicator.scope["user"] = AnonymousUser()
            self.communicator.scope["session"] = self.client.session

        await database_sync_to_async(logout_sync)()

        connected, _ = await self.communicator.connect()
        self.assertTrue(connected)
        response = await self.communicator.receive_json_from()

        # Expect 403 error response
        self.assertFalse(response["ok"])
        await self.communicator.receive_nothing(timeout=1, interval=0.1)

    async def test_websocket_connection_format(self):
        """
        Test that malformed data will not cause a server error
        """

        await self.setup()
        connected, _ = await self.communicator.connect()

        # Send invalid JSON
        await self.communicator.send_to(text_data="a")
        response = await self.communicator.receive_json_from()
        self.assertFalse(response["ok"])
        self.assertEqual(response["code"], 400)

        # Send bytes data
        await self.communicator.send_to(bytes_data=b"a")
        response = await self.communicator.receive_json_from()
        self.assertFalse(response["ok"])
        self.assertEqual(response["code"], 400)

        # Send JSON (not dict)
        await self.communicator.send_to(text_data="[]")
        response = await self.communicator.receive_json_from()
        self.assertFalse(response["ok"])
        self.assertEqual(response["code"], 400)

        # Send JSON (no action)
        await self.communicator.send_json_to({"type": "ping"})
        response = await self.communicator.receive_json_from()
        self.assertFalse(response["ok"])
        self.assertEqual(response["code"], 400)

        # Send JSON (invalid action)
        await self.communicator.send_json_to({"action": "invalid"})
        response = await self.communicator.receive_json_from()
        self.assertFalse(response["ok"])
        self.assertEqual(response["code"], 400)
        await self.communicator.send_json_to({"action": ["ping"]})
        response = await self.communicator.receive_json_from()
        self.assertFalse(response["ok"])
        self.assertEqual(response["code"], 400)

        # Send JSON (invalid request_id)
        await self.communicator.send_json_to({"action": "ping", "request_id": "a"})
        response = await self.communicator.receive_json_from()
        self.assertFalse(response["ok"])
        self.assertEqual(response["code"], 400)

    async def test_socket_request_id(self):
        """
        Test that request_id is correctly passed through
        """

        await self.setup()
        connected, _ = await self.communicator.connect()

        # Send ping request with request_id
        await self.communicator.send_json_to({"action": "ping", "request_id": 114514})
        response = await self.communicator.receive_json_from()
        self.assertTrue(response["ok"])
        self.assertEqual(response["action"], "pong")
        self.assertEqual(response["request_id"], 114514)

    async def create_chat(self) -> Chat:
        """
        Create a chat for testing
        """

        def create_chat_sync() -> Chat:
            self.assertTrue(create_user(self.client, "other"))
            self.other = get_user_by_name("other")
            self.assertTrue(create_friendship(self.client, "main", "other"))
            self.assertTrue(login_user(self.client, "main"))
            self.communicator.scope["session"] = self.client.session
            return Chat.objects.filter(name="").last()

        return await database_sync_to_async(create_chat_sync)()

    async def test_socket_send_message(self):
        """
        Test that sending a message works
        """

        await self.setup()
        chat = await self.create_chat()

        connected, _ = await self.communicator.connect()
        self.assertTrue(connected)

        # Send a message
        await self.communicator.send_json_to({
            "action": "send_message",
            "data": {
                "chat_id": chat.id,
                "content": "Hello, world!"
            },
        })

        # Check that there is a new-message event
        notification = await self.communicator.receive_json_from()
        self.assertEqual(notification["action"], "new_message")
        self.assertEqual(notification["data"]["message"]["chat_id"], chat.id)
        self.assertEqual(notification["data"]["message"]["message"], "Hello, world!")

        _ = await self.communicator.receive_json_from()

        # Send a message with reply_to
        reply_msg_id = notification["data"]["message"]["message_id"]
        await self.communicator.send_json_to({
            "action": "send_message",
            "data": {
                "chat_id": chat.id,
                "content": "REPLY",
                "reply_to": reply_msg_id,
            },
        })

        notification = await self.communicator.receive_json_from()
        self.assertEqual(notification["action"], "new_message")
        self.assertEqual(notification["data"]["message"]["chat_id"], chat.id)
        self.assertEqual(notification["data"]["message"]["message"], "REPLY")
        self.assertEqual(notification["data"]["message"]["reply_to_id"], reply_msg_id)

        _ = await self.communicator.receive_json_from()

    async def test_socket_send_message_invalid(self):
        """
        Try to send a message with invalid data
        """

        await self.setup()
        chat = await self.create_chat()

        # Create a test user
        def create_other_user() -> Chat:
            self.assertTrue(create_user(self.client, "u1"))
            self.assertTrue(create_friendship(self.client, "other", "u1"))
            chat2 = Chat.objects.all().last()
            self.assertTrue(login_user(self.client, "main"))
            self.communicator.scope["session"] = self.client.session
            return chat2

        chat2 = await database_sync_to_async(create_other_user)()

        connected, _ = await self.communicator.connect()
        self.assertTrue(connected)

        # Send a message with invalid data
        await self.communicator.send_json_to({
            "action": "send_message",
        })
        notification = await self.communicator.receive_json_from()
        self.assertFalse(notification["ok"])
        self.assertEqual(notification["code"], 400)

        # No chat_id
        await self.communicator.send_json_to({
            "action": "send_message",
            "data": {
                "content": "1",
            },
        })
        notification = await self.communicator.receive_json_from()
        self.assertFalse(notification["ok"])
        self.assertEqual(notification["code"], 400)

        # Invalid chat_id
        await self.communicator.send_json_to({
            "action": "send_message",
            "data": {
                "chat_id": 1234567,
                "content": "1",
            },
        })
        notification = await self.communicator.receive_json_from()
        self.assertFalse(notification["ok"])
        self.assertEqual(notification["code"], 400)

        # Other's chat
        await self.communicator.send_json_to({
            "action": "send_message",
            "data": {
                "chat_id": chat2.id,
                "content": "2",
            },
        })
        notification = await self.communicator.receive_json_from()
        self.assertFalse(notification["ok"])
        self.assertEqual(notification["code"], 400)

        # Invalid content
        await self.communicator.send_json_to({
            "action": "send_message",
            "data": {
                "chat_id": 1,
                "content": [],
            },
        })
        notification = await self.communicator.receive_json_from()
        self.assertFalse(notification["ok"])
        self.assertEqual(notification["code"], 400)

        # Empty content
        await self.communicator.send_json_to({
            "action": "send_message",
            "data": {
                "chat_id": 1,
                "content": "",
            },
        })
        notification = await self.communicator.receive_json_from()
        self.assertFalse(notification["ok"])
        self.assertEqual(notification["code"], 400)

        # Invalid reply_to
        await self.communicator.send_json_to({
            "action": "send_message",
            "data": {
                "chat_id": chat.id,
                "content": "AAA",
                "reply_to": "AAA",
            },
        })
        notification = await self.communicator.receive_json_from()
        self.assertFalse(notification["ok"])
        self.assertEqual(notification["code"], 400)

        await self.communicator.send_json_to({
            "action": "send_message",
            "data": {
                "chat_id": chat.id,
                "content": "AAA",
                "reply_to": -1,
            },
        })
        notification = await self.communicator.receive_json_from()
        self.assertFalse(notification["ok"])
        self.assertEqual(notification["code"], 400)

        # Reply to a message in another chat
        await self.communicator.send_json_to({
            "action": "send_message",
            "data": {
                "chat_id": chat.id,
                "content": "AAA",
                "reply_to": await database_sync_to_async(lambda: ChatMessage.objects.filter(chat=chat2).first().id)(),
            },
        })
        notification = await self.communicator.receive_json_from()
        self.assertFalse(notification["ok"])
        self.assertEqual(notification["code"], 400)

    async def test_recall_message(self):
        """
        Test recalling a message
        """

        await self.setup()
        chat = await self.create_chat()

        connected, _ = await self.communicator.connect()
        self.assertTrue(connected)

        # Send a message
        await self.communicator.send_json_to({
            "action": "send_message",
            "data": {
                "chat_id": chat.id,
                "content": "Message to recall"
            },
        })
        notification = await self.communicator.receive_json_from()

        # Ignore the message_read event
        _ = await self.communicator.receive_json_from()

        # Recall the message
        message_id = notification["data"]["message"]["message_id"]
        await self.communicator.send_json_to({
            "action": "recall_message",
            "data": {
                "message_id": message_id,
            },
        })

        # Check that there is a message-recalled event
        notification = await self.communicator.receive_json_from()
        self.assertEqual(notification["action"], "message_recalled")
        self.assertEqual(notification["data"]["message_id"], message_id)

        # Check that the message is recalled
        message = await database_sync_to_async(ChatMessage.objects.get)(id=message_id)
        self.assertTrue(message.deleted)

    async def test_recall_message_invalid(self):
        """
        Try to recall a message with invalid data
        """

        await self.setup()
        chat = await self.create_chat()

        connected, _ = await self.communicator.connect()
        self.assertTrue(connected)

        # Try to recall a system message
        sys_msg = await database_sync_to_async(
            lambda: ChatMessage.objects.filter(chat=chat, sender=User.magic_user_system()).first()
        )()
        await self.communicator.send_json_to({
            "action": "recall_message",
            "data": {
                "message_id": sys_msg.id,
            },
        })
        notification = await self.communicator.receive_json_from()
        self.assertFalse(notification["ok"])
        self.assertEqual(notification["code"], 400)

        # Try to recall a message that doesn't exist
        await self.communicator.send_json_to({
            "action": "recall_message",
            "data": {
                "message_id": -1,
            },
        })
        notification = await self.communicator.receive_json_from()
        self.assertFalse(notification["ok"])
        self.assertEqual(notification["code"], 400)

        # Invalid message_id
        await self.communicator.send_json_to({
            "action": "recall_message",
            "data": {
                "message_id": "AAA",
            },
        })
        notification = await self.communicator.receive_json_from()
        self.assertFalse(notification["ok"])
        self.assertEqual(notification["code"], 400)

    async def test_delete_message(self):
        """
        Test deleting a message
        """

        await self.setup()
        chat = await self.create_chat()

        connected, _ = await self.communicator.connect()
        self.assertTrue(connected)

        # Send a message
        await self.communicator.send_json_to({
            "action": "send_message",
            "data": {
                "chat_id": chat.id,
                "content": "Message to delete"
            },
        })
        notification = await self.communicator.receive_json_from()
        _ = await self.communicator.receive_json_from()

        # Delete the message
        message_id = notification["data"]["message"]["message_id"]
        await self.communicator.send_json_to({
            "action": "recall_message",
            "data": {
                "message_id": message_id,
                "delete": True
            },
        })

        # Check that there is a message-deleted event
        notification = await self.communicator.receive_json_from()
        self.assertEqual(notification["action"], "message_deleted")
        self.assertEqual(notification["data"]["message_id"], message_id)

        # Check that the message is deleted
        message = await database_sync_to_async(ChatMessage.objects.get)(id=message_id)
        self.assertTrue(await database_sync_to_async(lambda: self.user in message.deleted_users.all())())

    async def test_mark_chat_messages_read(self):
        """
        Test marking all messages in a chat as read
        """

        await self.setup()
        chat = await self.create_chat()

        connected, _ = await self.communicator.connect()
        self.assertTrue(connected)

        # Read all messages (now the system one)
        await self.communicator.send_json_to({
            "action": "messages_read",
            "data": {
                "chat_id": chat.id,
            },
        })

        # Check that there is a messages-read event
        notification = await self.communicator.receive_json_from()
        self.assertTrue(notification["ok"])
        self.assertEqual(notification["action"], "messages_read")

        # Check that all messages are read
        def check_msg_read_sync():
            messages = ChatMessage.objects.filter(chat=chat)
            for message in messages:
                self.assertTrue(self.user in message.read_users.all())

        await database_sync_to_async(check_msg_read_sync)()

        # Check that get chat info will return 0 unread messages
        def check_unread_sync():
            response = self.client.get(reverse("chat_get_delete", args=[chat.id]))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["data"]["unread_count"], 0)

        await database_sync_to_async(check_unread_sync)()

        # Try to mark messages in an invalid chat, for simplicity this isn't split into multiple tests
        await self.communicator.send_json_to({
            "action": "messages_read",
            "data": {
                "chat_id": -1,
            },
        })
        notification = await self.communicator.receive_json_from()
        self.assertFalse(notification["ok"])
        self.assertEqual(notification["code"], 400)
