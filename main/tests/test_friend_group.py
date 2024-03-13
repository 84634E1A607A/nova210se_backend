"""
Unit tests for friend_group-related APIs
"""

from main.models import FriendGroup
from django.test import TestCase
from django.urls import reverse
from .utils import create_user, get_user_by_name, JsonClient, login_user
from main.views.utils import friend_group_struct_by_model


class FriendGroupControlTests(TestCase):
    def setUp(self):
        self.client = JsonClient()

    def add_valid_friend_group(self, user_name: str, password: str = "test_password", group_name: str = "test_group"):
        """
        Helper function for adding a friend group
        """

        self.assertTrue(login_user(self.client, user_name=user_name, password=password))

        response = self.client.post(reverse("friend_group_add"), {
            "group_name": group_name
        })
        user = get_user_by_name(user_name=user_name)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["group_name"], group_name)
        self.assertEqual(FriendGroup.objects.get(name=group_name, user=user).name, group_name)
        self.assertEqual(FriendGroup.objects.get(name=group_name, user=user).user, user)

    def test_create_default_group(self):
        """
        Test default group is properly created
        """

        self.assertTrue(create_user(self.client, "u1"))

        response = self.client.get(reverse("friend_group_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]), 1)
        self.assertEqual(response.json()["data"][0]["group_name"], "")

    def test_delete_user_group(self):
        """
        Test groups are properly deleted when the user is deleted
        """

        self.assertTrue(create_user(self.client, "u1"))
        self.add_valid_friend_group(user_name="u1", group_name="test_group")
        user = get_user_by_name("u1")

        response = self.client.delete(reverse("user"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FriendGroup.objects.filter(user=user).count(), 0)

    def test_add_friend_group(self):
        """
        Test adding a friend group
        """

        self.assertTrue(create_user(self.client, "u1"))

        self.add_valid_friend_group(user_name="u1", group_name="test_group")

    def test_add_friend_group_with_repeated_name(self):
        """
        Test adding a friend group with repeated name
        """

        # Creat a user
        self.assertTrue(create_user(self.client, "u1"))

        # Add a group and check
        self.add_valid_friend_group(user_name="u1", group_name="test_group")

        # Add another group
        response = self.client.post(reverse("friend_group_add"), {
            "group_name": "test_group"
        })

        id_1 = FriendGroup.objects.filter(name="test_group")[0].id
        id_2 = FriendGroup.objects.filter(name="test_group")[1].id
        u1 = get_user_by_name("u1")

        # Check
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FriendGroup.objects.get(id=id_1).name, "test_group")
        self.assertEqual(FriendGroup.objects.get(id=id_2).name, "test_group")
        self.assertEqual(FriendGroup.objects.get(id=id_1).user, u1)
        self.assertEqual(FriendGroup.objects.get(id=id_2).user, u1)
        self.assertEqual(FriendGroup.objects.filter(name="test_group").count(), 2)

    def test_add_friend_group_long_name(self):
        """
        Test adding a friend group with name over 100 char
        """

        self.assertTrue(create_user(self.client, "u1"))

        group_name = "group_name" * 100
        response = self.client.post(reverse("friend_group_add"), {
            "group_name": group_name
        })

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_add_friend_group_empty_name(self):
        """
        Test adding a friend group with empty name
        """

        self.assertTrue(create_user(self.client, "u1"))

        response = self.client.post(reverse("friend_group_add"), {
            "group_name": ""
        })

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_get_friend_group_info_by_group_name(self):
        """
        Test getting a friend group info by group name
        """

        self.assertTrue(create_user(self.client, "u1"))

        self.add_valid_friend_group(user_name="u1", group_name="group1")

        # Get group info
        group = FriendGroup.objects.get(name="group1")
        response = self.client.get(reverse("friend_group_query", kwargs={"group_id": group.id}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], friend_group_struct_by_model(group))

    def test_get_friend_group_info_by_non_existent_group_name(self):
        """
        Test getting a friend group info by non-existent group name
        """

        self.assertTrue(create_user(self.client, "u1"))

        # Get group info
        response = self.client.get(reverse("friend_group_query", kwargs={"group_id": 123}))

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json()["ok"])

    def test_get_others_friend_group_info_by_group_name(self):
        """
        Test get a group from other user
        """

        self.assertTrue(create_user(self.client, "u1"))

        # Add groups
        self.add_valid_friend_group(user_name="u1", group_name="group1")

        # Creat and login another user
        self.assertTrue(create_user(self.client, "u2"))

        # Get group info
        response = self.client.get(reverse("friend_group_query", kwargs={
            "group_id": FriendGroup.objects.get(name="group1").id
        }))

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()["ok"])

    def test_get_friend_group_info_with_same_group_name(self):
        """
        Test get a group with repeated group name
        """

        # Creat a user and add group
        self.assertTrue(create_user(self.client, "u1"))
        self.add_valid_friend_group(user_name="u1", group_name="group1")

        # Creat another user and add group
        self.assertTrue(create_user(self.client, "u2"))
        self.add_valid_friend_group(user_name="u2", group_name="group1")

        filter_1 = FriendGroup.objects.filter(user=get_user_by_name("u1"), default=False)
        filter_2 = FriendGroup.objects.filter(user=get_user_by_name("u2"), default=False)

        # Check Group status
        self.assertEqual(FriendGroup.objects.filter(name="group1").count(), 2)
        self.assertEqual(filter_1.count(), 1)
        self.assertEqual(filter_2.count(), 1)
        self.assertEqual(filter_1.first().name, "group1")
        self.assertEqual(filter_2.first().name, "group1")
        self.assertEqual(filter_1.first().user, get_user_by_name("u1"))
        self.assertEqual(filter_2.first().user, get_user_by_name("u2"))

    def test_edit_friend_group_name(self):
        """
        Edit the group name
        """

        # Creat a user and add group
        self.assertTrue(create_user(self.client, "u1"))
        self.add_valid_friend_group(user_name="u1", group_name="group1")

        # Edit the group name
        response = self.client.patch(reverse("friend_group_query", kwargs={
            "group_id": FriendGroup.objects.get(name="group1").id
        }), {
            "group_name": "new name"
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(FriendGroup.objects.filter(name="group1").count(), 0)
        self.assertEqual(FriendGroup.objects.filter(name="new name").count(), 1)
        self.assertEqual(FriendGroup.objects.filter(name="new name").count(), 1)
        self.assertEqual(self.client.get(reverse("friend_group_query", kwargs={
            "group_id": FriendGroup.objects.get(name="new name").id
        })).status_code, 200)

    def test_edit_non_exist_group(self):
        """
        Edit a non-existent group
        """

        self.assertTrue(create_user(self.client, "u1"))
        self.add_valid_friend_group(user_name="u1", group_name="g1")

        # Edit the group name
        response = self.client.patch(reverse("friend_group_query", kwargs={
            "group_id": 123
        }), {
            "group_name": "new name"
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(FriendGroup.objects.filter(name="g1").count(), 1)
        self.assertEqual(FriendGroup.objects.filter(name="new name").count(), 0)
        self.assertEqual(self.client.get(reverse("friend_group_query", kwargs={
            "group_id": FriendGroup.objects.get(name="g1").id
        })).status_code, 200)

    def test_edit_others_group(self):
        """
        Edit other's group
        """

        self.assertTrue(create_user(self.client, "u1"))
        self.add_valid_friend_group(user_name="u1", group_name="g1")
        self.assertTrue(create_user(self.client, "u2"))
        self.add_valid_friend_group(user_name="u2", group_name="g2")

        login_user(self.client, "u1")

        response = self.client.patch(reverse("friend_group_query", kwargs={
            "group_id": FriendGroup.objects.get(name="g2").id
        }), {
            "group_name": "new name"
        })

        self.assertEqual(response.status_code, 403)
        self.assertEqual(FriendGroup.objects.filter(name="g2").count(), 1)
        self.assertEqual(FriendGroup.objects.filter(name="new name").count(), 0)

    def test_edit_default_group(self):
        """
        Try to edit a user's default group
        """

        self.assertTrue(create_user(self.client, "u1"))

        response = self.client.patch(reverse("friend_group_query", kwargs={
            "group_id": FriendGroup.objects.get(user=get_user_by_name("u1")).id
        }), {
            "group_name": "new name"
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(FriendGroup.objects.filter(name="").count(), 1)
        self.assertEqual(FriendGroup.objects.filter(name="new name").count(), 0)

    def test_change_group_name_to_empty(self):
        """
        Try to change group name to empty
        """

        self.assertTrue(create_user(self.client, "u1"))
        self.add_valid_friend_group(user_name="u1", group_name="g1")

        response = self.client.patch(reverse("friend_group_query", kwargs={
            "group_id": FriendGroup.objects.get(name="g1").id
        }), {
            "group_name": ""
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(FriendGroup.objects.filter(name="g1").count(), 1)
        self.assertEqual(FriendGroup.objects.filter(name="").count(), 1)

    def test_change_group_name_to_long(self):
        """
        Try to change group name to long
        """

        self.assertTrue(create_user(self.client, "u1"))
        self.add_valid_friend_group(user_name="u1", group_name="g1")

        group_name = "group_name" * 100
        response = self.client.patch(reverse("friend_group_query", kwargs={
            "group_id": FriendGroup.objects.get(name="g1").id
        }), {
            "group_name": group_name
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(FriendGroup.objects.filter(name="g1").count(), 1)
        self.assertEqual(FriendGroup.objects.filter(name=group_name).count(), 0)

    def test_delete_friend_group(self):
        """
        Delete a group
        """

        # Creat user and group
        self.assertTrue(create_user(self.client, user_name="u1"))
        self.add_valid_friend_group(user_name="u1", group_name="group1")

        # Delete the group
        _id = FriendGroup.objects.get(name="group1").id
        response = self.client.delete(reverse("friend_group_query", kwargs={
            "group_id": _id
        }))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(FriendGroup.objects.filter(name="group1").count(), 0)
        self.assertEqual(self.client.get(reverse("friend_group_query", kwargs={
            "group_id": _id
        })).status_code, 404)

    def test_delete_friend_group_with_non_existent_group(self):
        """
        Delete a group with non-existent group name
        """

        # Creat user and group
        self.assertTrue(create_user(self.client, user_name="u1"))
        self.add_valid_friend_group(user_name="u1", group_name="group1")

        # Try to delete a group with wrong id
        response = self.client.delete(reverse("friend_group_query", kwargs={
            "group_id": 123
        }))

        # Check
        self.assertEqual(response.status_code, 400)
        self.assertEqual(FriendGroup.objects.filter(name="group1").count(), 1)
        self.assertEqual(self.client.get(reverse("friend_group_query", kwargs={
            "group_id": FriendGroup.objects.get(name="group1").id
        })).status_code, 200)

    def test_delete_others_friend_group(self):
        """
        Test deleting others friend group
        """

        # Creat user and group
        self.assertTrue(create_user(self.client, user_name="u1"))
        self.add_valid_friend_group(user_name="u1", group_name="group1")

        # Creat and login another user
        self.assertTrue(create_user(self.client, user_name="u2"))

        # Try to delete others group
        response = self.client.delete(reverse("friend_group_query", kwargs={
            "group_id": FriendGroup.objects.get(name="group1").id
        }))

        # Check
        self.assertEqual(response.status_code, 403)
        self.assertEqual(FriendGroup.objects.filter(name="group1").count(), 1)
        self.assertEqual(self.client.get(reverse("friend_group_query", kwargs={
            "group_id": FriendGroup.objects.get(name="group1").id
        })).status_code, 403)

        login_user(self.client, user_name="u1")
        self.assertEqual(self.client.get(reverse("friend_group_query", kwargs={
            "group_id": FriendGroup.objects.get(name="group1").id
        })).status_code, 200)

    def test_delete_default_group(self):
        """
        Try to delete a user's default group
        """

        # Creat user and group
        self.assertTrue(create_user(self.client, user_name="u1"))

        # Try to delete default group
        response = self.client.delete(reverse("friend_group_query", kwargs={
            "group_id": FriendGroup.objects.get(user=get_user_by_name("u1")).id
        }))

        # Check
        self.assertEqual(response.status_code, 400)
        self.assertEqual(FriendGroup.objects.count(), 1)

    def test_list_groups(self):
        """
        List the group of a user
        """

        # Creat user and groups
        self.assertTrue(create_user(self.client, user_name="u1"))
        self.add_valid_friend_group(user_name="u1", group_name="group1")
        self.add_valid_friend_group(user_name="u1", group_name="group2")

        # Get list
        response = self.client.get(reverse("friend_group_list"))

        group1 = FriendGroup.objects.get(name="group1")
        group2 = FriendGroup.objects.get(name="group2")
        default_group = FriendGroup.objects.get(user=get_user_by_name("u1"), default=True)

        # Check
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FriendGroup.objects.filter(user=get_user_by_name("u1"), default=False).count(), 2)
        self.assertEqual(response.json()["data"], [
            friend_group_struct_by_model(default_group),
            friend_group_struct_by_model(group1),
            friend_group_struct_by_model(group2),
        ])

    def test_list_group_with_multi_users(self):
        """
        List group with different user
        """

        # Creat user and group
        self.assertTrue(create_user(self.client, user_name="u1"))
        self.add_valid_friend_group(user_name="u1", group_name="group1")

        # Get list
        response = self.client.get(reverse("friend_group_list"))

        # Check
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FriendGroup.objects.filter(user=get_user_by_name("u1"), default=False).count(), 1)
        self.assertEqual(response.json()["data"], [
            friend_group_struct_by_model(FriendGroup.objects.get(user=get_user_by_name("u1"), default=True)),
            friend_group_struct_by_model(FriendGroup.objects.get(name="group1")),
        ])

        # Creat another user and group
        self.assertTrue(create_user(self.client, user_name="u2"))
        self.add_valid_friend_group(user_name="u2", group_name="group2")

        # Get list
        response = self.client.get(reverse("friend_group_list"))

        # Check
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FriendGroup.objects.filter(user=get_user_by_name("u2"), default=False).count(), 1)
        self.assertEqual(response.json()["data"], [
            friend_group_struct_by_model(FriendGroup.objects.get(user=get_user_by_name("u2"), default=True)),
            friend_group_struct_by_model(FriendGroup.objects.get(name="group2", )),
        ])
