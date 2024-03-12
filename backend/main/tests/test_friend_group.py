"""
Unit tests for friend_group-related APIs
"""

from main.models import FriendGroup
from django.test import TestCase, Client
from django.urls import reverse
from .utils import create_user, get_user_by_authuser_name
from main.views.utils import friend_group_struct_by_model


class FriendGroupControlTests(TestCase):
    def setUp(self):
        self.client = Client()

    def add_valid_friend_group(self, user_name: str, group_name: str = "test_group"):
        """
        Helper function for adding a friend group
        """

        response = self.client.post(reverse("friend_group_add"), {
            "group_name": group_name
        }, content_type="application/json")
        user = get_user_by_authuser_name(user_name=user_name)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["group_name"], group_name)
        self.assertEqual(FriendGroup.objects.get(name=group_name, user=user).name, group_name)
        self.assertEqual(FriendGroup.objects.get(name=group_name, user=user).user, user)

    def test_add_friend_group(self):
        """
        Test adding a friend group
        """

        self.assertTrue(create_user(self.client, "u1"))

        self.add_valid_friend_group(user_name="u1", group_name="test_group")

    def test_add_friend_group_long_name(self):
        """
        Test adding a friend group with name over 100 char
        """

        self.assertTrue(create_user(self.client, "u1"))

        group_name = "group_name" * 100
        response = self.client.post(reverse("friend_group_add"), {
            "group_name": group_name
        }, content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_add_friend_group_empty_name(self):
        """
        Test adding a friend group with empty name
        """

        self.assertTrue(create_user(self.client, "u1"))

        response = self.client.post(reverse("friend_group_add"), {
            "group_name": ""
        }, content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_add_friend_group_with_non_string(self):
        """
        Test adding a friend group with non-string name
        """

        self.assertTrue(create_user(self.client, "u1"))

        response = self.client.post(reverse("friend_group_add"), {
            "group_name": 123
        }, content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    def test_add_friend_group_without_login(self):
        """
        Test adding a friend group without logining a user
        """

        response = self.client.post(reverse("friend_group_add"), {
            "group_name": ""
        }, content_type="application/json")

        self.assertEqual(response.status_code, 403)
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

        filter_1 = FriendGroup.objects.filter(user=get_user_by_authuser_name("u1"))
        filter_2 = FriendGroup.objects.filter(user=get_user_by_authuser_name("u2"))

        # Check Group status
        self.assertEqual(FriendGroup.objects.filter(name="group1").count(), 2)
        self.assertEqual(filter_1.count(), 1)
        self.assertEqual(filter_2.count(), 1)
        self.assertEqual(filter_1.first().name, "group1")
        self.assertEqual(filter_2.first().name, "group1")
        self.assertEqual(filter_1.first().user, get_user_by_authuser_name("u1"))
        self.assertEqual(filter_2.first().user, get_user_by_authuser_name("u2"))

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
        }, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(FriendGroup.objects.filter(name="group1").count(), 0)
        self.assertEqual(FriendGroup.objects.filter(name="new name").count(), 1)
        self.assertEqual(FriendGroup.objects.get(user=get_user_by_authuser_name("u1")).name, "new name")
        self.assertEqual(self.client.get(reverse("friend_group_query", kwargs={
            "group_id": FriendGroup.objects.get(name="new name").id
        })).status_code, 200)

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
