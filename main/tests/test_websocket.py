"""
Unit tests for main websocket
"""
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from channels.testing import WebsocketCommunicator

from main.tests.utils import JsonClient, create_user, get_user_by_name, logout_user
from main.ws import MainWebsocketConsumer


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
