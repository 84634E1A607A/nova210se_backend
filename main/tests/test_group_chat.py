"""
Unit-tests for group chat APIs
"""

from main.models import User, Chat, ChatMessage, ChatInvitation, UserChatRelation
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

        # Users
        u1 = get_user_by_name("u1")
        u2 = get_user_by_name("u2")
        u3 = get_user_by_name("u3")
        u4 = get_user_by_name("u4")

        # Chats
        c21 = Chat.objects.filter(owner=u2)[0]
        c31 = Chat.objects.filter(owner=u3)[0]
        c32 = Chat.objects.filter(owner=u3)[1]
        c41 = Chat.objects.filter(owner=u4)[0]

        self.assertEqual(Chat.objects.count(), 4)
        self.assertEqual(Chat.objects.filter(owner=u1).count(), 0)
        self.assertEqual(Chat.objects.filter(owner=u2).count(), 1)
        self.assertEqual(Chat.objects.filter(owner=u3).count(), 2)
        self.assertEqual(Chat.objects.filter(owner=u4).count(), 1)

        self.assertTrue(UserChatRelation.objects.filter(user=u1, chat=c21).count(), 1)
        self.assertTrue(UserChatRelation.objects.filter(user=u2, chat=c21).count(), 1)
        self.assertTrue(UserChatRelation.objects.filter(chat=c31).count(), 2)
        self.assertTrue(UserChatRelation.objects.filter(chat=c32).count(), 2)
        self.assertTrue(UserChatRelation.objects.filter(chat=c41).count(), 2)

    def test_initial_message(self):
        """
        Check that the initial message is sent correctly
        """

        self.assertEqual(ChatMessage.objects.count(), 4)
        for chat in Chat.objects.all():
            self.assertEqual(ChatMessage.objects.filter(chat=chat).count(), 1)
            self.assertEqual(
                ChatMessage.objects.filter(chat=chat).first().message,
                f"{chat.owner.auth_user.username} added {chat.members.all()[0].auth_user.username} as a friend"
            )

    def test_create_chat(self):
        """
        Check that creating a chat works
        """

        # Create a group with two people
        chat_id = self.create_chat("Test chat", [self.users[0], self.users[1]])
        chat = Chat.objects.get(id=chat_id)
        members_str = ", ".join([self.users[0].auth_user.username, self.users[1].auth_user.username])
        self.assertEqual(chat.name, "Test chat")
        self.assertEqual(chat.owner, self.users[0])
        self.assertEqual(chat.admins.count(), 0)
        self.assertEqual(chat.members.count(), 2)
        self.assertEqual(
            ChatMessage.objects.filter(chat=chat).first().message,
            f"Group Test chat created by {self.users[0].auth_user.username} with {members_str}"
        )

        # Create a group with one one person, owner itself
        chat_id = self.create_chat("Lonely chat", [self.users[0]])
        chat = Chat.objects.get(id=chat_id)
        self.assertEqual(chat.name, "Lonely chat")
        self.assertEqual(chat.owner, self.users[0])
        self.assertEqual(chat.admins.count(), 0)
        self.assertEqual(chat.members.count(), 1)
        self.assertEqual(
            ChatMessage.objects.filter(chat=chat).first().message,
            f"Group Lonely chat created by {self.users[0].auth_user.username} with {self.users[0].auth_user.username}"
        )

        # # Create a group with owner itself again
        chat_id = self.create_chat("Lonely chat", [self.users[0]])
        chat = Chat.objects.get(id=chat_id)
        self.assertEqual(chat.name, "Lonely chat")
        self.assertEqual(Chat.objects.filter(name="Lonely chat").count(), 2)

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

    def test_create_chat_invalid_name(self):
        """
        Check that creating a chat with an invalid name fails
        """

        self.assertTrue(login_user(self.client, "u1"))

        # Empty chat name
        response = self.client.post(reverse("chat_new"), {
            "chat_name": "",
            "chat_members": [self.users[0].id, self.users[1].id]
        })
        self.assertEqual(response.status_code, 400)

        # Long chat name
        response = self.client.post(reverse("chat_new"), {
            "chat_name": "NAME"*60,
            "chat_members": [self.users[0].id, self.users[1].id]
        })
        self.assertEqual(response.status_code, 400)

        # None chat name
        response = self.client.post(reverse("chat_new"), {
            "chat_name": None,
            "chat_members": [self.users[0].id, self.users[1].id]
        })
        self.assertEqual(response.status_code, 400)

        # Wrong format name
        response = self.client.post(reverse("chat_new"), {
            "chat_name": 123,
            "chat_members": [self.users[0].id, self.users[1].id]
        })
        self.assertEqual(response.status_code, 400)

    def test_delete_user(self):
        """
        Check that deleting a user moves related chat messages to #DELETED
        """

        ch = self.create_chat("Test chat", [self.users[0], self.users[1], self.users[2]])

        # Login to u2
        self.assertTrue(login_user(self.client, "u2"))
        # Create a chat message manually
        ChatMessage.objects.create(chat_id=ch, sender=self.users[1], message="Test message")
        # Delete the user
        self.client.delete(reverse("user"))

        self.assertEqual(ChatMessage.objects.filter(sender=User.magic_user_deleted()).count(), 1)
        self.assertEqual(ChatMessage.objects.filter(sender=User.magic_user_deleted()).first().message, "Test message")

        # Login to u3
        self.assertTrue(login_user(self.client, "u3"))
        # Create a chat message manually
        ChatMessage.objects.create(chat_id=ch, sender=self.users[2], message="Second message")
        # Delete the user again
        self.client.delete(reverse("user"))

        self.assertEqual(ChatMessage.objects.filter(sender=User.magic_user_deleted()).count(), 2)
        self.assertEqual(ChatMessage.objects.filter(sender=User.magic_user_deleted())[1].message, "Second message")

        # Login to u1 (owner)
        self.assertTrue(login_user(self.client, "u1"))
        # Delete the owner
        self.client.delete(reverse("user"))

        self.assertEqual(ChatMessage.objects.filter(sender=User.magic_user_deleted()).count(), 0)
        self.assertEqual(ChatMessage.objects.filter(chat__id=ch).count(), 0)

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
        self.assertEqual(Chat.objects.get(id=cid).members.count(), 2)

    def test_invite_to_chat_wrong_user(self):
        """
        Check that inviting a non-existent / non-friend user or yourself or someone already in the chat to a chat fails
        """

        cid = self.create_chat("Test chat", [self.users[1], self.users[0]])

        self.assertTrue(login_user(self.client, "u1"))

        # User does not exist
        response = self.client.post(reverse("chat_invite", kwargs={"chat_id": cid}), {
            "user_id": 10
        })
        self.assertEqual(response.status_code, 400)

        # User that is not friend to inviter
        response = self.client.post(reverse("chat_invite", kwargs={"chat_id": cid}), {
            "user_id": self.users[4].id
        })
        self.assertEqual(response.status_code, 400)

        # User already in chat
        response = self.client.post(reverse("chat_invite", kwargs={"chat_id": cid}), {
            "user_id": self.users[0].id
        })
        self.assertEqual(response.status_code, 400)

        # Inviter itself
        response = self.client.post(reverse("chat_invite", kwargs={"chat_id": cid}), {
            "user_id": self.users[1].id
        })
        self.assertEqual(response.status_code, 400)

        # Wrong user id format
        response = self.client.post(reverse("chat_invite", kwargs={"chat_id": cid}), {
            "user_id": [0, 1]
        })
        self.assertEqual(response.status_code, 400)

        self.assertEqual(ChatInvitation.objects.count(), 0)
        self.assertEqual(Chat.objects.get(id=cid).members.count(), 2)

    def test_invite_to_chat_not_member(self):
        """
        Check that inviting a user to a chat that the inviter is not a member of fails
        """

        cid = self.create_chat("Test chat", [self.users[0], self.users[3]])

        self.assertTrue(login_user(self.client, "u3"))

        response = self.client.post(reverse("chat_invite", kwargs={"chat_id": cid}), {
            "user_id": self.users[1].id
        })

        self.assertEqual(response.status_code, 403)
        self.assertEqual(ChatInvitation.objects.count(), 0)
        self.assertEqual(Chat.objects.get(id=cid).members.count(), 2)

    def test_invite_to_chat_wrong_chat_id(self):
        """
        Check that inviting a user to a non-existing chat
        """

        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.post(reverse("chat_invite", kwargs={"chat_id": 123}), {
            "user_id": self.users[1].id
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ChatInvitation.objects.count(), 0)

    def test_invite_to_private_chat(self):
        """
        Check that inviting a user to a private chat
        """

        self.assertTrue(login_user(self.client, "u3"))
        u3 = get_user_by_name("u3")
        pc_id = Chat.objects.filter(owner=u3).first().id

        response = self.client.post(reverse("chat_invite", kwargs={"chat_id": pc_id}), {
            "user_id": self.users[1].id
        })
        self.assertEqual(response.status_code, 400)

        self.assertEqual(ChatInvitation.objects.count(), 0)

    def test_list_chat_group_invitations_owner(self):
        """
        Test listing all pending invitations by owner
        """

        # Create a chat group
        cid = self.create_chat("Test chat", [self.users[0]])

        # Login to u1(owner) and invite u2 and u3 to the chat
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.post(reverse("chat_invite", kwargs={"chat_id": cid}), {
            "user_id": self.users[1].id
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ChatInvitation.objects.count(), 1)
        response = self.client.post(reverse("chat_invite", kwargs={"chat_id": cid}), {
            "user_id": self.users[2].id
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ChatInvitation.objects.count(), 2)

        # Get the invitation list
        response = self.client.get(reverse("chat_list_invitation", kwargs={"chat_id": cid}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], [
            ChatInvitation.objects.filter(user=self.users[1]).first().to_struct(),
            ChatInvitation.objects.filter(user=self.users[2]).first().to_struct()
        ])

    def test_list_chat_group_invitations_admin(self):
        """
        Test listing all pending invitations by admin
        """

        # Create a chat group
        cid = self.create_chat("Test chat", [self.users[0], self.users[1]])

        # Login to u1 and set u2 as admin
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.post(reverse("chat_set_admin", kwargs={
            "chat_id": cid,
            "member_id": self.users[1].id
        }), data="true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Chat.objects.filter(id=cid).first().admins.first().to_detailed_struct(),
                         self.users[1].to_detailed_struct())

        # Send invitation to u3
        response = self.client.post(reverse("chat_invite", kwargs={"chat_id": cid}), {
            "user_id": self.users[2].id
        })

        # Login to u2(admin) and get invitation list
        self.assertTrue(login_user(self.client, "u2"))
        response = self.client.get(reverse("chat_list_invitation", kwargs={"chat_id": cid}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], [
            ChatInvitation.objects.filter(user=self.users[2]).first().to_struct(),
        ])

    def test_list_chat_group_invitations_non_owner_admin(self):
        """
        Test listing all pending invitations by a non-admin/owner user
        """

        # Create a chat group
        cid = self.create_chat("Test chat", [self.users[0]])

        # Login to u1(owner) and invite u2 to the chat
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.post(reverse("chat_invite", kwargs={"chat_id": cid}), {
            "user_id": self.users[1].id
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ChatInvitation.objects.count(), 1)

        # Login to u2 and try to list invitation
        self.assertTrue(login_user(self.client, "u2"))
        response = self.client.get(reverse("chat_list_invitation", kwargs={"chat_id": cid}))
        self.assertEqual(response.status_code, 403)

    def test_list_chat_group_invitations_non_exist_group(self):
        """
        Test listing all pending invitations of a non_existing group
        """

        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.get(reverse("chat_list_invitation", kwargs={"chat_id": 123}))
        self.assertEqual(response.status_code, 400)

    def test_accept_reject_chat_group_invitation(self):
        """
        Accept and reject a chat group invitation by admin/owner
        """

        # Create a chat group
        cid = self.create_chat("Test chat", [self.users[0], self.users[1]])

        # Login to u1 and set u2 as admin
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.post(reverse("chat_set_admin", kwargs={
            "chat_id": cid,
            "member_id": self.users[1].id
        }), data="true")
        self.assertEqual(response.status_code, 200)

        # Invite u3 and u4 into the chat
        response = self.client.post(reverse("chat_invite", kwargs={"chat_id": cid}), {
            "user_id": self.users[2].id
        })
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("chat_invite", kwargs={"chat_id": cid}), {
            "user_id": self.users[3].id
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ChatInvitation.objects.count(), 2)

        # u1(owner) reject the invitation to u3
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.delete(reverse("chat_respond_to_invitation", kwargs={
            "chat_id": cid,
            "user_id": self.users[2].id
        }))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ChatInvitation.objects.count(), 1)
        self.assertEqual(Chat.objects.filter(id=cid).first().members.count(), 2)

        # u2(admin) accept the invitation to u4
        self.assertTrue(login_user(self.client, "u2"))
        response = self.client.post(reverse("chat_respond_to_invitation", kwargs={
            "chat_id": cid,
            "user_id": self.users[3].id
        }))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ChatInvitation.objects.count(), 0)
        self.assertEqual(Chat.objects.filter(id=cid).first().members.count(), 3)
        self.assertEqual(ChatMessage.objects.filter(chat__id=cid).last().message,
                         f"u2 approved u4 to join the group, invited by u1")
        self.assertTrue(UserChatRelation.objects.filter(user=self.users[3], chat__id=cid).exists())

    def test_accept_reject_chat_group_invitation_non_owner_admin(self):
        """
        Test accepting and rejecting a chat group invitation by a non-admin/owner user
        """

        # Create a chat group
        cid = self.create_chat("Test chat", [self.users[0], self.users[1]])

        # Login to u1 and invite u3
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.post(reverse("chat_invite", kwargs={"chat_id": cid}), {
            "user_id": self.users[2].id
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ChatInvitation.objects.count(), 1)

        # Login to u2 and try to accept and reject the invitation
        self.assertTrue(login_user(self.client, "u2"))
        response = self.client.post(reverse("chat_respond_to_invitation", kwargs={
            "chat_id": cid,
            "user_id": self.users[2].id
        }))
        self.assertEqual(response.status_code, 403)
        response = self.client.delete(reverse("chat_respond_to_invitation", kwargs={
            "chat_id": cid,
            "user_id": self.users[2].id
        }))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(ChatInvitation.objects.count(), 1)
        self.assertEqual(Chat.objects.filter(id=cid).first().members.count(), 2)
