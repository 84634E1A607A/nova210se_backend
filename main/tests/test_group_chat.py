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
        self.client.post(reverse("chat_invite", kwargs={"chat_id": cid}), {
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

    def test_list_chats(self):
        """
        List all chats of the current user
        """

        # Create chat groups
        self.assertTrue(login_user(self.client, "u1"))
        cid1 = self.create_chat("chat1", [self.users[0], self.users[1]])
        cid2 = self.create_chat("chat2", [self.users[0], self.users[1], self.users[2]])
        cid3 = self.create_chat("chat3", [self.users[0]])

        # List and check for u1
        response = self.client.get(reverse("chat_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], [
            {'chat': Chat.objects.get(id=1).to_struct(), 'nickname': '', 'unread_count': 1},
            {'chat': Chat.objects.get(id=2).to_struct(), 'nickname': '', 'unread_count': 1},
            {'chat': Chat.objects.get(id=3).to_struct(), 'nickname': '', 'unread_count': 1},
            {'chat': Chat.objects.get(id=cid1).to_struct(), 'nickname': '', 'unread_count': 1},
            {'chat': Chat.objects.get(id=cid2).to_struct(), 'nickname': '', 'unread_count': 1},
            {'chat': Chat.objects.get(id=cid3).to_struct(), 'nickname': '', 'unread_count': 1},
        ])

        # List and check for u3
        self.assertTrue(login_user(self.client, "u3"))
        response = self.client.get(reverse("chat_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], [
            {'chat': Chat.objects.get(id=2).to_struct(), 'nickname': '', 'unread_count': 1},
            {'chat': Chat.objects.get(id=4).to_struct(), 'nickname': '', 'unread_count': 1},
            {'chat': Chat.objects.get(id=cid2).to_struct(), 'nickname': '', 'unread_count': 1},
        ])

    def test_get_chat_info(self):
        """
        Get a chat info by chat id
        """

        # Create chat groups
        cid1 = self.create_chat("chat1", [self.users[0], self.users[1]])
        cid2 = self.create_chat("chat2", [self.users[0], self.users[1], self.users[2]])

        # Login to u1 and get chat info
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.get(reverse("chat_get_delete", kwargs={"chat_id": 1}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"],
                         UserChatRelation.objects.filter(user=self.users[0], chat__id=1).first().to_struct())
        response = self.client.get(reverse("chat_get_delete", kwargs={"chat_id": cid1}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"],
                         UserChatRelation.objects.filter(user=self.users[0], chat__id=cid1).first().to_struct())
        response = self.client.get(reverse("chat_get_delete", kwargs={"chat_id": cid2}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"],
                         UserChatRelation.objects.filter(user=self.users[0], chat__id=cid2).first().to_struct())

        # Login to u3 and get chat info
        self.assertTrue(login_user(self.client, "u3"))
        response = self.client.get(reverse("chat_get_delete", kwargs={"chat_id": cid2}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"],
                         UserChatRelation.objects.filter(user=self.users[2], chat__id=cid2).first().to_struct())

    def test_get_chat_info_others_group(self):
        """
        Get a chat info which the current user is not a member of the chat
        """

        # Create chat groups
        cid1 = self.create_chat("chat1", [self.users[0], self.users[1]])

        # Log in to u3 and try to get u1u2's chat group info
        self.assertTrue(login_user(self.client, "u3"))
        response = self.client.get(reverse("chat_get_delete", kwargs={"chat_id": cid1}))
        self.assertEqual(response.status_code, 400)

    def test_get_chat_info_non_existing_group(self):
        """
        Get a chat info which the chat does not exist
        """

        # Login to u1 and try to get a chat group info
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.get(reverse("chat_get_delete", kwargs={"chat_id": 123}))
        self.assertEqual(response.status_code, 400)

    def test_leave_chat_group(self):
        """
        Leave a chat group
        """

        # Create chat group
        cid = self.create_chat("chat1", [self.users[0], self.users[1]])

        # Login u2 and leave the chat
        self.assertTrue(login_user(self.client, "u2"))
        self.assertEqual(UserChatRelation.objects.filter(user=self.users[1]).count(), 3)

        response = self.client.delete(reverse("chat_get_delete", kwargs={"chat_id": cid}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Chat.objects.filter(id=cid).first().members.count(), 1)
        self.assertEqual(UserChatRelation.objects.filter(user=self.users[1]).count(), 2)
        self.assertEqual(ChatMessage.objects.filter(chat__id=cid).last().message,
                         f"u2 left the chat")

    def test_leave_chat_group_with_problem(self):
        """
        Test leaving a chat group with the case:
        group does not exist, user is not a member, group is private
        """

        # Create chat group
        cid = self.create_chat("chat1", [self.users[1], self.users[2]])

        # Group does not exist
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.delete(reverse("chat_get_delete", kwargs={"chat_id": 123}))
        self.assertEqual(response.status_code, 400)

        # User is not a member
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.delete(reverse("chat_get_delete", kwargs={"chat_id": cid}))
        self.assertEqual(response.status_code, 400)

        # Group is private
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.delete(reverse("chat_get_delete", kwargs={"chat_id": 1}))
        self.assertEqual(response.status_code, 400)

    def test_leave_chat_group_owner(self):
        """
        Test an owner leave the chat
        """

        # Create chat group
        cid = self.create_chat("chat1", [self.users[0], self.users[1], self.users[2]])
        self.assertEqual(UserChatRelation.objects.filter(user=self.users[0]).count(), 4)
        self.assertEqual(UserChatRelation.objects.filter(user=self.users[1]).count(), 3)
        self.assertEqual(UserChatRelation.objects.filter(user=self.users[2]).count(), 3)

        # Login to u1 and leave the group
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.delete(reverse("chat_get_delete", kwargs={"chat_id": cid}))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Chat.objects.filter(id=cid).exists())
        self.assertEqual(UserChatRelation.objects.filter(user=self.users[0]).count(), 3)
        self.assertEqual(UserChatRelation.objects.filter(user=self.users[1]).count(), 2)
        self.assertEqual(UserChatRelation.objects.filter(user=self.users[2]).count(), 2)

    def test_leave_chat_group_admin(self):
        """
        Test an admin leave the chat
        """

        # Create chat group
        cid = self.create_chat("chat1", [self.users[0], self.users[1], self.users[2]])

        # Login to u1 and set u2 as admin
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.post(reverse("chat_set_admin", kwargs={
            "chat_id": cid,
            "member_id": self.users[1].id
        }), data="true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Chat.objects.filter(id=cid).first().members.count(), 3)

        # u2 leaves the chat and check
        self.assertTrue(login_user(self.client, "u2"))
        response = self.client.delete(reverse("chat_get_delete", kwargs={"chat_id": cid}))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Chat.objects.filter(id=cid).exists())
        self.assertEqual(Chat.objects.filter(id=cid).first().admins.count(), 0)
        self.assertEqual(Chat.objects.filter(id=cid).first().members.count(), 2)
        self.assertEqual(UserChatRelation.objects.filter(user=self.users[1]).count(), 2)
        self.assertEqual(ChatMessage.objects.filter(chat__id=cid).last().message,
                         f"u2 left the chat")

    def test_get_messages(self):
        """
        Get all messages in a chat with chat id
        """

        # Create chat group
        cid = self.create_chat("chat1", [self.users[0], self.users[1], self.users[2]])

        # Login to u1 and get all messages
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.get(reverse("chat_list_messages", kwargs={"chat_id": cid}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], [
            ChatMessage.objects.filter(chat__id=cid, sender=User.magic_user_system()).first().to_detailed_struct()
        ])

        # Send a message in chat
        ChatMessage.objects.create(chat_id=cid, sender=self.users[0], message="This is a message")
        response = self.client.get(reverse("chat_list_messages", kwargs={"chat_id": cid}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], [
            ChatMessage.objects.filter(chat__id=cid, sender=self.users[0]).first().to_detailed_struct(),
            ChatMessage.objects.filter(chat__id=cid, sender=User.magic_user_system()).first().to_detailed_struct()
        ])

    def test_get_messages_fail(self):
        """
        Try to get all message when the group does not exist or
        user is not a group member
        """

        # Create chat group
        cid = self.create_chat("chat1", [self.users[0], self.users[1]])

        # Login to u3(not a member) and get messages
        self.assertTrue(login_user(self.client, "u3"))
        response = self.client.get(reverse("chat_list_messages", kwargs={"chat_id": cid}))
        self.assertEqual(response.status_code, 403)

        # Try to get a group message which the group does not exist
        response = self.client.get(reverse("chat_list_messages", kwargs={"chat_id": 123}))
        self.assertEqual(response.status_code, 404)

    def test_set_unset_admin(self):
        """
        Set and unset a group member to admin
        """

        # Create chat group
        cid = self.create_chat("chat1", [self.users[0], self.users[1], self.users[2]])

        # Login to u1(owner) and set u2 and u3 as admin
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.post(reverse("chat_set_admin", kwargs={
            "chat_id": cid,
            "member_id": self.users[1].id
        }), data="true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Chat.objects.filter(id=cid).first().admins.count(), 1)
        self.assertEqual(Chat.objects.filter(id=cid).first().admins.first(), self.users[1])
        response = self.client.post(reverse("chat_set_admin", kwargs={
            "chat_id": cid,
            "member_id": self.users[2].id
        }), data="true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Chat.objects.filter(id=cid).first().admins.count(), 2)
        self.assertEqual(Chat.objects.filter(id=cid).first().admins.last(), self.users[2])

        # Unset u2 to non-admin
        response = self.client.post(reverse("chat_set_admin", kwargs={
            "chat_id": cid,
            "member_id": self.users[1].id
        }), data="false")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Chat.objects.filter(id=cid).first().admins.count(), 1)
        self.assertEqual(Chat.objects.filter(id=cid).first().admins.first(), self.users[2])

    def test_set_admin_fail(self):
        """
        Try to set an admin in the following cases:
        wrong json format,
        group does not exist,
        chat is private,
        a non-owner user set member to admin,
        set the owner to admin,
        user is not in group
        """

        # Create chat group
        cid = self.create_chat("chat1", [self.users[0], self.users[1], self.users[2]])

        # json format is incorrect
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.post(reverse("chat_set_admin", kwargs={
            "chat_id": cid,
            "member_id": self.users[2].id
        }), data="123")
        self.assertEqual(response.status_code, 400)

        # group does not exist
        response = self.client.post(reverse("chat_set_admin", kwargs={
            "chat_id": 123,
            "member_id": self.users[2].id
        }), data="true")
        self.assertEqual(response.status_code, 400)

        # set an admin in private group
        response = self.client.post(reverse("chat_set_admin", kwargs={
            "chat_id": 1,
            "member_id": self.users[2].id
        }), data="true")
        self.assertEqual(response.status_code, 400)

        # Login to u2(non-owner) and set u3 as admin
        self.assertTrue(login_user(self.client, "u2"))
        response = self.client.post(reverse("chat_set_admin", kwargs={
            "chat_id": cid,
            "member_id": self.users[2].id
        }), data="true")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Chat.objects.filter(id=cid).first().admins.count(), 0)

        # Login to u1(owner) and set himself as admin
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.post(reverse("chat_set_admin", kwargs={
            "chat_id": cid,
            "member_id": self.users[0].id
        }), data="true")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Chat.objects.filter(id=cid).first().admins.count(), 0)

        # user is not in group
        response = self.client.post(reverse("chat_set_admin", kwargs={
            "chat_id": cid,
            "member_id": self.users[3].id
        }), data="true")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Chat.objects.filter(id=cid).first().admins.count(), 0)

    def test_set_admin_to_admin(self):
        """
        Try to set an admin/non-admin to admin/non-admin
        """

        # Create chat group
        cid = self.create_chat("chat1", [self.users[0], self.users[1], self.users[2]])

        # Login to u1(owner) and set u2 as admin
        self.assertTrue(login_user(self.client, "u1"))
        self.client.post(reverse("chat_set_admin", kwargs={
            "chat_id": cid,
            "member_id": self.users[1].id
        }), data="true")
        self.assertEqual(Chat.objects.filter(id=cid).first().admins.count(), 1)

        # Try to set u2(admin) as admin
        response = self.client.post(reverse("chat_set_admin", kwargs={
            "chat_id": cid,
            "member_id": self.users[1].id
        }), data="true")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Chat.objects.filter(id=cid).first().admins.count(), 1)

        # Try to unset u3(non-admin) to num-admin
        response = self.client.post(reverse("chat_set_admin", kwargs={
            "chat_id": cid,
            "member_id": self.users[2].id
        }), data="false")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Chat.objects.filter(id=cid).first().admins.count(), 1)

    def test_set_owner(self):
        """
        Set a member to be owner in chat group
        """

        # Create chat group
        cid = self.create_chat("chat1", [self.users[0], self.users[1], self.users[2]])

        # Login to u1(owner) and set u2 as admin
        self.assertTrue(login_user(self.client, "u1"))
        self.client.post(reverse("chat_set_admin", kwargs={
            "chat_id": cid,
            "member_id": self.users[1].id
        }), data="true")
        self.assertEqual(Chat.objects.filter(id=cid).first().admins.count(), 1)
        self.assertEqual(Chat.objects.filter(id=cid).first().admins.first(), self.users[1])

        # Set u2 as owner
        response = self.client.post(reverse("chat_set_owner", kwargs={"chat_id": cid}), data={
            "chat_owner": self.users[1].id
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Chat.objects.filter(id=cid).first().owner, self.users[1])
        self.assertEqual(Chat.objects.filter(id=cid).first().admins.count(), 1)
        self.assertEqual(Chat.objects.filter(id=cid).first().admins.first(), self.users[0])

        # Login to u2(new owner) and set u3 as owner
        self.assertTrue(login_user(self.client, "u2"))
        response = self.client.post(reverse("chat_set_owner", kwargs={"chat_id": cid}), data={
            "chat_owner": self.users[2].id
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Chat.objects.filter(id=cid).first().owner, self.users[2])
        self.assertEqual(Chat.objects.filter(id=cid).first().admins.count(), 2)
        self.assertEqual(Chat.objects.filter(id=cid).first().admins.first(), self.users[0])
        self.assertEqual(Chat.objects.filter(id=cid).first().admins.last(), self.users[1])

    def test_set_owner_fail(self):
        """
        Try to set an owner in the following cases:
        a non-owner user set member to owner,
        group does not exist,
        chat is private,
        set the owner to owner,
        user is not in group
        """

        # Create chat group
        cid = self.create_chat("chat1", [self.users[0], self.users[1], self.users[2]])

        # Login to u2(non-owner) and set u3 as admin
        self.assertTrue(login_user(self.client, "u2"))
        response = self.client.post(reverse("chat_set_owner", kwargs={"chat_id": cid}), data={
            "chat_owner": self.users[2].id
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Chat.objects.filter(id=cid).first().owner, self.users[0])

        # group does not exist
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.post(reverse("chat_set_owner", kwargs={"chat_id": 123}), data={
            "chat_owner": self.users[1].id
        })
        self.assertEqual(response.status_code, 400)

        # set an owner in private group
        response = self.client.post(reverse("chat_set_owner", kwargs={"chat_id": 1}), data={
            "chat_owner": self.users[1].id
        })
        self.assertEqual(response.status_code, 400)

        # Login to u1(owner) and set himself as admin
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.post(reverse("chat_set_owner", kwargs={"chat_id": cid}), data={
            "chat_owner": self.users[0].id
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Chat.objects.filter(id=cid).first().owner, self.users[0])

        # user is not in group
        response = self.client.post(reverse("chat_set_owner", kwargs={"chat_id": cid}), data={
            "chat_owner": self.users[3].id
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Chat.objects.filter(id=cid).first().owner, self.users[0])

        self.assertEqual(Chat.objects.filter(id=cid).first().admins.count(), 0)

    def test_remove_member(self):
        """
        Remove a member from a chat
        """

        # Create chat group
        cid = self.create_chat("chat1", [self.users[0], self.users[1], self.users[2]])

        # Login to u1(owner) and set u2 as admin
        self.assertTrue(login_user(self.client, "u1"))
        self.client.post(reverse("chat_set_admin", kwargs={
            "chat_id": cid,
            "member_id": self.users[1].id
        }), data="true")

        # Login to u2(admin) and remove u3
        self.assertTrue(login_user(self.client, "u2"))
        response = self.client.delete(reverse("chat_remove_member", kwargs={
            "chat_id": cid,
            "member_id": self.users[2].id
        }))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Chat.objects.filter(id=cid).first().members.count(), 2)
        self.assertFalse(UserChatRelation.objects.filter(user=self.users[2], chat__id=cid).exists())
        self.assertEqual(ChatMessage.objects.filter(chat__id=cid, sender=User.magic_user_system()).last().message,
                         f"u2 removed u3 from the group")

        # Login to u1(owner) and remove u2(admin)
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.delete(reverse("chat_remove_member", kwargs={
            "chat_id": cid,
            "member_id": self.users[1].id
        }))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Chat.objects.filter(id=cid).first().members.count(), 1)
        self.assertEqual(Chat.objects.filter(id=cid).first().admins.count(), 0)
        self.assertFalse(UserChatRelation.objects.filter(user=self.users[1], chat__id=cid).exists())
        self.assertEqual(ChatMessage.objects.filter(chat__id=cid, sender=User.magic_user_system()).last().message,
                         f"u1 removed u2 from the group")

    def test_remove_member_fail(self):
        """
        Try to remove a member in the following cases:
        group does not exist,
        chat is private,
        user is not in group,
        a non-owner/admin user remove a member,
        an admin remove the owner,
        an admin remove an admin,
        an owner remove itself
        """

        # Create chat group
        cid = self.create_chat("chat1", [self.users[0], self.users[1], self.users[2]])

        # Login to u1(owner) and set u2 as admin
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.post(reverse("chat_set_admin", kwargs={
            "chat_id": cid,
            "member_id": self.users[1].id
        }), data="true")
        self.assertEqual(response.status_code, 200)

        # group does not exist
        response = self.client.delete(reverse("chat_remove_member", kwargs={
            "chat_id": 123,
            "member_id": self.users[2].id
        }))
        self.assertEqual(response.status_code, 400)

        # chat is private
        response = self.client.delete(reverse("chat_remove_member", kwargs={
            "chat_id": 1,
            "member_id": self.users[2].id
        }))
        self.assertEqual(response.status_code, 400)

        # user is not in group
        response = self.client.delete(reverse("chat_remove_member", kwargs={
            "chat_id": cid,
            "member_id": self.users[3].id
        }))
        self.assertEqual(response.status_code, 400)

        # a non-owner/admin user remove a member
        self.assertTrue(login_user(self.client, "u3"))
        response = self.client.delete(reverse("chat_remove_member", kwargs={
            "chat_id": cid,
            "member_id": self.users[0].id
        }))
        self.assertEqual(response.status_code, 403)

        # an admin remove the owner
        self.assertTrue(login_user(self.client, "u2"))
        response = self.client.delete(reverse("chat_remove_member", kwargs={
            "chat_id": cid,
            "member_id": self.users[0].id
        }))
        self.assertEqual(response.status_code, 403)

        # an admin remove an admin
        response = self.client.delete(reverse("chat_remove_member", kwargs={
            "chat_id": cid,
            "member_id": self.users[1].id
        }))
        self.assertEqual(response.status_code, 403)

        # an owner remove itself
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.delete(reverse("chat_remove_member", kwargs={
            "chat_id": cid,
            "member_id": self.users[0].id
        }))
        self.assertEqual(response.status_code, 403)
