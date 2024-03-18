"""test_create_user
Unit tests for user-related APIs
"""

from main.models import User, AuthUser, FriendInvitation, Friend
from main.views.utils import user_struct_by_model, friend_invitation_struct_by_model
from django.test import TestCase
from django.urls import reverse
from .utils import create_user, login_user, logout_user, JsonClient, get_user_by_name


class UserControlTests(TestCase):
    def setUp(self):
        self.client = JsonClient()

    def send_invitation_via_search(self, sender_name, receiver_name, comment=":)"):
        """
        Login to sender_name, send an invitation to receiver_name, and logout

        :param sender_name: sender's name, this user must exist or the test will fail
        :param receiver_name: receiver's name, this user must also exist
        :param comment: comment to send
        """

        self.assertTrue(login_user(self.client, sender_name))
        response = self.client.post(reverse("friend_invite"), {
            "id": User.objects.get(auth_user__username=receiver_name).id,
            "source": "search",
            "comment": comment
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(logout_user(self.client))

    def test_find_friend_by_id(self):
        """
        Find a user by id
        """

        self.assertTrue(create_user(self.client, user_name="u1"))
        self.assertTrue(create_user(self.client, user_name="u2"))

        # Get id
        _id1 = User.objects.get(auth_user=AuthUser.objects.get(username="u1")).id

        # Find the user by id
        response = self.client.post(reverse("friend_find"), {
            "id": _id1,
        })

        self.assertEqual(response.status_code, 200)
        u1 = User.objects.get(id=_id1)
        self.assertEqual(response.json()["data"], [user_struct_by_model(u1)])

    def test_find_friend_by_id_fail(self):
        """
        Find a user with non-existing id
        """

        self.assertTrue(create_user(self.client, user_name="u1"))
        self.assertTrue(create_user(self.client, user_name="u2"))

        # Find the user by id
        response = self.client.post(reverse("friend_find"), {
            "id": 123,
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], [])

    def test_find_friend_by_id_self(self):
        """
        Find a user by its own id
        """

        self.assertTrue(create_user(self.client, user_name="u1"))

        # Find the user by id
        response = self.client.post(reverse("friend_find"), {
            "id": User.objects.get(auth_user__username="u1").id,
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], [])

    def test_find_friend_by_name_fail(self):
        """
        Find a user with non-existing keywords
        """

        self.assertTrue(create_user(self.client, user_name="u1"))

        # Find the user by name
        response = self.client.post(reverse("friend_find"), {
            "name_contains": "3",
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], [])

    def test_find_friend_by_name_without_itself(self):
        """
        Find users containing keywords without user itself
        """

        self.assertTrue(create_user(self.client, user_name="u1"))
        self.assertTrue(create_user(self.client, user_name="u11"))
        self.assertTrue(create_user(self.client, user_name="u2"))

        # Find the user by name
        response = self.client.post(reverse("friend_find"), {
            "name_contains": "u1",
        })

        self.assertEqual(response.status_code, 200)
        u1 = User.objects.get(auth_user=AuthUser.objects.get(username="u1"))
        u11 = User.objects.get(auth_user=AuthUser.objects.get(username="u11"))
        self.assertEqual(response.json()["data"], [user_struct_by_model(u1), user_struct_by_model(u11)])

    def test_find_friend_by_name_with_itself(self):
        """
        Find users containing keywords with user itself
        """

        # Create users and logout the first two
        self.assertTrue(create_user(self.client, user_name="u1"))
        self.assertTrue(create_user(self.client, user_name="u11"))

        # Find the user by name
        response = self.client.post(reverse("friend_find"), {
            "name_contains": "u1",
        })

        self.assertEqual(response.status_code, 200)
        u1 = User.objects.get(auth_user=AuthUser.objects.get(username="u1"))
        self.assertEqual(response.json()["data"], [user_struct_by_model(u1)])

    def test_find_friend_without_condition(self):
        """
        Find users without any condition set
        """

        # Create users and logout the first two
        self.assertTrue(create_user(self.client, user_name="u1"))

        # Find the user by name
        response = self.client.post(reverse("friend_find"), {})

        self.assertEqual(response.status_code, 400)

    def test_send_invitation_from_search(self):
        """
        Send an invitation to a user
        """

        sender_name, receiver_name = "u1", "u2"

        # Create users and logout the first one
        self.assertTrue(create_user(self.client, user_name=receiver_name))
        self.assertTrue(create_user(self.client, user_name=sender_name))

        # u2 send invitation to u1
        response = self.client.post(reverse("friend_invite"), {
            "id": User.objects.get(auth_user=AuthUser.objects.get(username=receiver_name)).id,
            "source": "search",
            "comment": ":)"
        })

        # Check
        self.assertEqual(response.status_code, 200)
        u1 = User.objects.get(auth_user=AuthUser.objects.get(username=receiver_name))
        u2 = User.objects.get(auth_user=AuthUser.objects.get(username=sender_name))

        # Check sender invitation info
        invitation_by_sender = FriendInvitation.objects.get(sender=u2)
        # Check receiver invitation info
        invitation_by_receiver = FriendInvitation.objects.get(receiver=u1)
        self.assertEqual(invitation_by_sender, invitation_by_receiver)

    def test_send_invitation_from_search_non_existent(self):
        """
        Send an invitation to a non-existent user and user
        """

        self.assertTrue(create_user(self.client, user_name="u1"))

        # Send invitation to a non-existing user
        response = self.client.post(reverse("friend_invite"), {
            "id": 123,
            "source": "search",
            "comment": ":)"
        })

        # Check
        self.assertEqual(response.status_code, 400)
        self.assertEqual(FriendInvitation.objects.filter(sender__auth_user__username="u1").count(), 0)

    def test_send_invitation_to_oneself(self):
        """
        Send an invitation to the user itself
        """

        self.assertTrue(create_user(self.client, user_name="u1"))

        response = self.client.post(reverse("friend_invite"), {
            "id": User.objects.get(auth_user__username="u1").id,
            "source": "search",
            "comment": "?"
        })

        # Check
        self.assertEqual(response.status_code, 400)
        self.assertEqual(FriendInvitation.objects.filter(sender__auth_user__username="u1").count(), 0)

    def test_send_invitation_with_invalid_source(self):
        """
        Send an invitation with source neither "group_id" nor "search"
        """

        self.assertTrue(create_user(self.client, user_name="u1"))
        self.assertTrue(create_user(self.client, user_name="u2"))

        # Send invitation with weird source
        response = self.client.post(reverse("friend_invite"), {
            "id": User.objects.get(auth_user=AuthUser.objects.get(username="u1")).id,
            "source": "haha",
            "comment": ":)"
        })

        # Check
        self.assertEqual(response.status_code, 400)
        self.assertEqual(FriendInvitation.objects.filter(sender__auth_user__username="u1").count(), 0)

    def test_send_invitation_with_no_source(self):
        """
        Send an invitation with no source
        """

        self.assertTrue(create_user(self.client, user_name="u1"))
        self.assertTrue(create_user(self.client, user_name="u2"))

        # Send invitation with weird source
        response = self.client.post(reverse("friend_invite"), {
            "id": User.objects.get(auth_user=AuthUser.objects.get(username="u1")).id,
            "comment": ":)"
        })

        # Check
        self.assertEqual(response.status_code, 400)
        self.assertEqual(FriendInvitation.objects.filter(sender__auth_user__username="u1").count(), 0)

    def test_accept_invitation_via_send_invitation(self):
        """
        Accept an invitation by sending an invitation to the sender
        """

        self.assertTrue(create_user(self.client, user_name="u1"))
        self.assertTrue(create_user(self.client, user_name="u2"))

        self.send_invitation_via_search("u1", "u2")
        self.send_invitation_via_search("u2", "u1")

        # Check
        self.assertEqual(FriendInvitation.objects.count(), 0)
        self.assertEqual(Friend.objects.count(), 2)

    def test_invitation_conflict(self):
        """
        Sending invitation to a friend
        """

        self.assertTrue(create_user(self.client, user_name="u1"))
        self.assertTrue(create_user(self.client, user_name="u2"))

        self.send_invitation_via_search("u1", "u2")
        self.send_invitation_via_search("u2", "u1")

        login_user(self.client, "u1")
        response = self.client.post(reverse("friend_invite"), {
            "id": User.objects.get(auth_user__username="u2").id,
            "source": "search",
            "comment": "Conflict!"
        })

        # Check
        self.assertEqual(response.status_code, 409)
        self.assertEqual(FriendInvitation.objects.count(), 0)

    def test_send_multiple_invitations_from_search(self):
        """
        Send invitations to multiple users
        """

        # Create users
        self.assertTrue(create_user(self.client, "u1"))
        self.assertTrue(create_user(self.client, "u2"))
        self.assertTrue(create_user(self.client, "u3"))
        u1 = get_user_by_name("u1")
        u2 = get_user_by_name("u2")
        u3 = get_user_by_name("u3")

        # Send invitations
        self.send_invitation_via_search("u1", "u2")
        self.send_invitation_via_search("u1", "u3")

        # Check
        self.assertEqual(FriendInvitation.objects.filter(sender=u1).count(), 2)
        self.assertEqual(FriendInvitation.objects.filter(receiver=u2).count(), 1)
        self.assertEqual(FriendInvitation.objects.filter(receiver=u3).count(), 1)

    def test_send_invitation_same_receiver(self):
        """
        Send an invitation to a user twice
        """

        # Create users
        self.assertTrue(create_user(self.client, "u1"))
        self.assertTrue(create_user(self.client, "u2"))
        u1 = get_user_by_name("u1")
        u2 = get_user_by_name("u2")

        self.send_invitation_via_search("u1", "u2")
        self.send_invitation_via_search("u1", "u2", ":(")
        _id2 = FriendInvitation.objects.get(sender=u1).id
        self.assertEqual(FriendInvitation.objects.filter(sender=u1).count(), 1)
        self.assertEqual(FriendInvitation.objects.filter(receiver=u2).count(), 1)
        self.assertEqual(FriendInvitation.objects.get(id=_id2).comment, ":(")

    def test_receive_multiple_invitations(self):
        """
        Receive multiple invitations from other users
        """

        # Create users
        self.assertTrue(create_user(self.client, "r"))
        self.assertTrue(create_user(self.client, "u2"))
        self.assertTrue(create_user(self.client, "u3"))
        u1 = get_user_by_name("r")
        u2 = get_user_by_name("u2")
        u3 = get_user_by_name("u3")

        # Send invitations
        self.send_invitation_via_search("u2", "r")
        self.send_invitation_via_search("u3", "r")

        # Check
        self.assertEqual(FriendInvitation.objects.get(sender=u2).receiver, u1)
        self.assertEqual(FriendInvitation.objects.get(sender=u3).receiver, u1)
        self.assertEqual(FriendInvitation.objects.filter(receiver=u1)[0].sender, u2)
        self.assertEqual(FriendInvitation.objects.filter(receiver=u1)[1].sender, u3)

    def test_send_invitation_twice_wrong_format(self):
        """
        Send an invitation to u1, and send again but it's invalid
        """

        # Create users
        self.assertTrue(create_user(self.client, "u1"))
        self.assertTrue(create_user(self.client, "u2"))
        u1 = get_user_by_name("u1")
        u2 = get_user_by_name("u2")

        # u1 send invitation to u2
        self.send_invitation_via_search("u1", "u2")

        # u1 send to u2 again but invalid source
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.post(reverse("friend_invite"), {
            "id": get_user_by_name("u2").id,
            "source": "haha",
            "comment": ":("
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(FriendInvitation.objects.filter(sender=u1).count(), 1)
        self.assertEqual(FriendInvitation.objects.filter(receiver=u2).count(), 1)
        self.assertEqual(FriendInvitation.objects.get(sender=u1).comment, ":)")

    def test_list_invitations(self):
        """
        List all invitations related to current user
        """

        # Create users and send invitations
        self.assertTrue(create_user(self.client, "u1"))
        self.assertTrue(create_user(self.client, "u2"))
        self.assertTrue(create_user(self.client, "u3"))
        u2 = get_user_by_name("u2")
        u3 = get_user_by_name("u3")
        self.send_invitation_via_search("u2", "u1")
        self.send_invitation_via_search("u3", "u1")

        # Login to u1 and get the invitation list
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.get(reverse("friend_list_invitation"))

        # Check
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]), 2)
        self.assertEqual(response.json()["data"], [
            friend_invitation_struct_by_model(FriendInvitation.objects.get(sender=u2)),
            friend_invitation_struct_by_model(FriendInvitation.objects.get(sender=u3))
        ])

        # Login to u2 and try to get the invitation list
        self.assertTrue(login_user(self.client, "u2"))
        response = self.client.get(reverse("friend_list_invitation"))

        # Check
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]), 0)
        self.assertEqual(response.json()["data"], [])

    def test_accept_invitation(self):
        """
        Accept an invitation
        """

        # Create users and send invitation
        self.assertTrue(create_user(self.client, "u1"))
        self.assertTrue(create_user(self.client, "u2"))
        u1 = get_user_by_name("u1")
        u2 = get_user_by_name("u2")
        self.send_invitation_via_search("u1", "u2")

        # Accept the invitation
        self.assertTrue(login_user(self.client, "u2"))
        response = self.client.post(reverse("friend_accept_invitation", kwargs={
            "invitation_id": FriendInvitation.objects.get(sender=u1).id
        }))

        # Check
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Friend.objects.get(user=u2).friend, u1)
        self.assertEqual(Friend.objects.get(user=u1).friend, u2)
        self.assertEqual(Friend.objects.get(friend=u2).user, u1)
        self.assertEqual(Friend.objects.get(friend=u1).user, u2)

    def test_accept_invitation_not_exist(self):
        """
        Accept an non-existent invitation
        """

        self.assertTrue(create_user(self.client, "u1"))

        # Accept an arbitrary invitation
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.post(reverse("friend_accept_invitation", kwargs={
            "invitation_id": 32123
        }))

        # Check
        self.assertEqual(response.status_code, 400)

    def test_accept_others_invitation(self):
        """
        Accept other's invitation
        """

        # Create users and send invitation
        self.assertTrue(create_user(self.client, "u1"))
        self.assertTrue(create_user(self.client, "u2"))
        self.send_invitation_via_search("u1", "u2")

        # Accept the invitation
        self.assertTrue(login_user(self.client, "u1"))
        response = self.client.post(reverse("friend_accept_invitation", kwargs={
            "invitation_id": FriendInvitation.objects.first().id
        }))

        # Check
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Friend.objects.count(), 0)
        self.assertEqual(FriendInvitation.objects.count(), 1)