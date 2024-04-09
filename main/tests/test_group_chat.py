"""
Unit-tests for group chat APIs
"""

from main.models import User, Chat, ChatMessage, ChatInvitation
from django.test import TestCase
from django.urls import reverse

from main.tests.utils import JsonClient, create_user, get_user_by_name, create_friendship, login_user


class GroupChatTests(TestCase):
    def setUp(self):
        """
        Setup for group chat tests

        5 users are created:
        u1, friendship with u2-u4
        u2, friendship with u1,u3
        u3, friendship with u1,u2
        u4, friendship with u1
        u5, no friendships
        """

        self.client = JsonClient()

        self.users: list[User] = []
        # For group chat tests, just create multiple users and friendships
        for i in range(1, 6):
            self.assertTrue(create_user(self.client, f"u{i}"))
            self.users.append(get_user_by_name(f"u{i}"))

        # Create friendships
        self.assertTrue(create_friendship(self.client, "u1", "u2"))
        self.assertTrue(create_friendship(self.client, "u1", "u3"))
        self.assertTrue(create_friendship(self.client, "u1", "u4"))
        self.assertTrue(create_friendship(self.client, "u2", "u3"))

    def create_chat(self, name: str, members: list[User]) -> int:
        """
        Create a chat with the given members. The owner is the first member in the list.

        The owner is kept logged in after the chat is created.

        returns the chat ID
        """

        self.assertTrue(login_user(self.client, members[0].auth_user.username))

        response = self.client.post(reverse("chat_new"), {
            "chat_name": name,
            "chat_members": [member.id for member in members]
        })

        self.assertEqual(response.status_code, 200)
        return response.json()["data"]["chat_id"]

    def test_default_chat(self):
        """
        Check that private chats are created by default
        """

        self.assertEqual(Chat.objects.count(), 4)

    def test_initial_message(self):
        """
        Check that the initial message is sent correctly
        """

        self.assertEqual(ChatMessage.objects.count(), 4)
        for chat in Chat.objects.all():
            self.assertEqual(ChatMessage.objects.filter(chat=chat).count(), 1)

    def test_create_chat(self):
        """
        Check that creating a chat works
        """

        chat_id = self.create_chat("Test chat", [self.users[0], self.users[1]])
        chat = Chat.objects.get(id=chat_id)
        self.assertEqual(chat.name, "Test chat")
        self.assertEqual(chat.owner, self.users[0])
        self.assertEqual(chat.admins.count(), 0)
        self.assertEqual(chat.members.count(), 2)

    def test_create_chat_wrong_members_format(self):
        """
        Check that creating a chat with wrong members format fails
        """

        self.assertTrue(login_user(self.client, "u1"))

        response = self.client.post(reverse("chat_new"), {
            "chat_name": "Test chat",
            "chat_members": [""]
        })

        self.assertEqual(response.status_code, 400)

        response = self.client.post(reverse("chat_new"), {
            "chat_name": "Test chat",
            "chat_members": [10]
        })

        self.assertEqual(response.status_code, 400)

        response = self.client.post(reverse("chat_new"), {
            "chat_name": "Test chat",
            "chat_members": [self.users[4].id]
        })

        self.assertEqual(response.status_code, 400)

    def test_create_chat_empty_name(self):
        """
        Check that creating a chat with an empty name fails
        """

        self.assertTrue(login_user(self.client, "u1"))

        response = self.client.post(reverse("chat_new"), {
            "chat_name": "",
            "chat_members": [self.users[0].id, self.users[1].id]
        })

        self.assertEqual(response.status_code, 400)

    def test_delete_user(self):
        """
        Check that deleting a user moves related chat messages to #DELETED
        """

        ch = self.create_chat("Test chat", [self.users[0], self.users[1]])

        self.assertTrue(login_user(self.client, "u2"))

        # Create a chat message manually
        ChatMessage.objects.create(chat_id=ch, sender=self.users[1], message="Test message")

        # Delete the user
        self.client.delete(reverse("user"))

        self.assertEqual(ChatMessage.objects.filter(sender=User.magic_user_deleted()).count(), 1)
        self.assertEqual(ChatMessage.objects.filter(sender=User.magic_user_deleted()).first().message, "Test message")

    def test_invite_to_chat(self):
        """
        Check that inviting a user to a chat works
        """

        cid = self.create_chat("Test chat", [self.users[1], self.users[0]])

        self.assertTrue(login_user(self.client, "u1"))

        response = self.client.post(reverse("chat_invite", kwargs={"chat_id": cid}), {
            "user_id": self.users[2].id
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ChatInvitation.objects.count(), 1)
        # self.assertEqual(Chat.objects.get(id=cid).members.count(), 3)
        # self.assertTrue(self.users[2] in Chat.objects.get(id=cid).members.all())
        #
        # # System message is sent
        # self.assertEqual(ChatMessage.objects.filter(chat_id=cid).count(), 2)

    def test_invite_to_chat_wrong_user(self):
        """
        Check that inviting a non-existent / non-friend user or yourself or someone already in the chat to a chat fails
        """

        cid = self.create_chat("Test chat", [self.users[1], self.users[0]])

        self.assertTrue(login_user(self.client, "u1"))

        response = self.client.post(reverse("chat_invite", kwargs={"chat_id": cid}), {
            "user_id": 10
        })

        self.assertEqual(response.status_code, 400)

        response = self.client.post(reverse("chat_invite", kwargs={"chat_id": cid}), {
            "user_id": self.users[4].id
        })

        self.assertEqual(response.status_code, 400)

        response = self.client.post(reverse("chat_invite", kwargs={"chat_id": cid}), {
            "user_id": self.users[0].id
        })

        self.assertEqual(response.status_code, 400)

        response = self.client.post(reverse("chat_invite", kwargs={"chat_id": cid}), {
            "user_id": self.users[1].id
        })

        self.assertEqual(response.status_code, 400)

        self.assertEqual(Chat.objects.get(id=cid).members.count(), 2)

    def test_invite_to_chat_not_member(self):
        """
        Check that inviting a user to a chat you are not a member of fails
        """

        cid = self.create_chat("Test chat", [self.users[0], self.users[3]])

        self.assertTrue(login_user(self.client, "u3"))

        response = self.client.post(reverse("chat_invite", kwargs={"chat_id": cid}), {
            "user_id": self.users[1].id
        })

        self.assertEqual(response.status_code, 403)

        self.assertEqual(Chat.objects.get(id=cid).members.count(), 2)
