"""
Unit tests for user-related APIs
"""

from main.models import User
from django.test import TestCase
from django.urls import reverse

from main.tests.utils import JsonClient


class UserControlTests(TestCase):
    def setUp(self):
        self.client = JsonClient()

    def test_bad_json(self):
        """
        Test a bad JSON request
        """

        response = self.client.post(reverse("user_register"), "{This is not JSON}")
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["ok"])

    def test_bad_content_type(self):
        """
        Test a bad content type
        """

        response = self.client.post(reverse("user_register"), "password=", content_type="multipart/form-data")
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["ok"])

    def test_404_page(self):
        """
        Test the 404 page
        """

        response = self.client.get("/this_page_does_not_exist")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.headers["Content-Type"], "application/json")
        data = response.json()
        self.assertFalse(data["ok"])

    def test_create_user(self):
        """
        Create a test user and log in
        """

        response = self.client.post(reverse("user_register"), {
            "user_name": "test_user",
            "password": "test_password"
        })

        # Check response status
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])

        # Check user is created
        user_id = data["data"]["id"]
        self.assertTrue(User.objects.filter(id=user_id).exists())

        # Check information is correct
        user = User.objects.get(id=user_id)
        self.assertEqual(data["data"]["user_name"], user.auth_user.username)
        self.assertTrue(user.auth_user.check_password("test_password"))

        # Check user is logged in
        self.assertEqual(self.client.get(reverse("user")).status_code, 200)

    def test_logout_user(self):
        """
        Log out a test user
        """

        # Create user
        self.test_create_user()

        # Log out
        response = self.client.post(reverse("user_logout"), content_type="")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(reverse("user")).status_code, 403)

    def test_login_user(self):
        """
        Login to a test user
        """

        # Create user and log out
        self.test_create_user()
        self.client.post(reverse("user_logout"), content_type="")

        # Log in
        response = self.client.post(reverse("user_login"), {
            "user_name": "test_user",
            "password": "test_password"
        })

        # Check response status
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])

        # Check user is logged in
        self.assertEqual(self.client.get(reverse("user")).status_code, 200)

    def test_login_user_fail_password(self):
        """
        Login to a test user with incorrect password
        """

        # Create user
        self.test_create_user()

        # Log in (wrong pass)
        response = self.client.post(reverse("user_login"), {
            "user_name": "test_user",
            "password": "wrong_password"
        })

        # Check response status
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data["ok"])

    def test_login_user_fail_user(self):
        """
        Login to a test user with non-exist username
        """

        # Create user
        self.test_create_user()

        # Log in (wrong user)
        response = self.client.post(reverse("user_login"), {
            "user_name": "wrong_user",
            "password": "test_password"
        })

        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data["ok"])

    def test_login_user_fail_no_user_name(self):
        """
        Login to a test user with no user_name field
        """

        # Create user
        self.test_create_user()

        # Log in (no username)
        response = self.client.post(reverse("user_login"), {
            "password": "test_password"
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["ok"])

    def test_create_duplicate_user(self):
        """
        Create a duplicate user
        """

        # Create user
        self.test_create_user()

        # Create duplicate user
        response = self.client.post(reverse("user_register"), {
            "user_name": "test_user",
            "password": "test_password_2"
        })

        # Check response status
        self.assertEqual(response.status_code, 409)
        data = response.json()
        self.assertFalse(data["ok"])

    def test_create_user_with_empty_name(self):
        """
        Create a user with no name
        """

        response = self.client.post(reverse("user_register"), {
            "user_name": "",
            "password": "test_password"
        })

        # Check response status
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["ok"])

    def test_create_user_with_long_name(self):
        """
        Create a user with a very long name
        """

        response = self.client.post(reverse("user_register"), {
            "user_name": "a" * 1000,
            "password": "test_password"
        })

        # Check response status
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["ok"])

    def test_create_user_with_invalid_name(self):
        """
        Create a user with an invalid name
        """

        response = self.client.post(reverse("user_register"), {
            "user_name": "a-ZA-z&&*??:;",
            "password": "test_password"
        })

        # Check response status
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["ok"])

    def test_get_user_info(self):
        """
        Get user info
        """

        # Create user
        self.test_create_user()

        # Get user
        response = self.client.get(reverse("user"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["user_name"], "test_user")

    def test_delete_user(self):
        """
        Delete a user
        """

        # Create user
        self.test_create_user()

        _id = self.client.get(reverse("user")).json()["data"]["id"]

        # Delete user
        response = self.client.delete(reverse("user"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(reverse("user")).status_code, 403)
        self.assertFalse(User.objects.filter(id=_id).exists())

    def test_modify_user_password(self):
        """
        Modify a user's password
        """

        # Create user
        self.test_create_user()

        # Modify user
        response = self.client.patch(reverse("user"), {
            "old_password": "test_password",
            "new_password": "new_password"
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.first().auth_user.check_password("new_password"))

    def test_modify_user_password_fail(self):
        """
        Modify a user's password with wrong old password
        """

        # Create user
        self.test_create_user()

        # Modify user
        response = self.client.patch(reverse("user"), {
            "old_password": "wrong_password",
            "new_password": "new_password"
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.first().auth_user.check_password("new_password"))

    def test_modify_user_password_too_short(self):
        """
        Modify a user's password with short password
        """

        # Create user
        self.test_create_user()

        # Modify user
        response = self.client.patch(reverse("user"), {
            "old_password": "test_password",
            "new_password": "1234"
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.first().auth_user.check_password("1234"))

    def test_modify_user_password_with_whitespace(self):
        """
        Modify a user's password containing whitespace
        """

        # Create user
        self.test_create_user()

        # Modify user
        response = self.client.patch(reverse("user"), {
            "old_password": "test_password",
            "new_password": "1 2 3 4 5 6 7 8 9"
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.first().auth_user.check_password("1 2 3 4 5 6 7 8 9"))

    def test_modify_user_avatar(self):
        """
        Modify a user's avatar
        """

        # Create user
        self.test_create_user()

        avatar_url = "https://localhost:8000/avatar.jpg"

        # Modify user
        response = self.client.patch(reverse("user"), {
            "avatar_url": avatar_url
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["avatar_url"], avatar_url)

    def test_modify_user_avatar_non_http(self):
        """
        Try to set a non-HTTP avatar URL
        """

        # Create user
        self.test_create_user()

        # Modify user
        response = self.client.patch(reverse("user"), {
            "avatar_url": "invalid_avatar_url"
        })
        self.assertEqual(response.status_code, 400)

    def test_modify_user_avatar_too_long(self):
        """
        Try to set a very long avatar URL
        """

        # Create user
        self.test_create_user()

        # Modify user
        response = self.client.patch(reverse("user"), {
            "avatar_url": "https://localhost:8000/" + "blabla" * 500
        })
        self.assertEqual(response.status_code, 400)

    def test_get_user_by_id(self):
        """
        Get a user by ID
        """

        # Create user
        self.test_create_user()

        # Get user
        _id = User.objects.first().id
        response = self.client.get(reverse("user_by_id", kwargs={"_id": _id}))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.json()["data"]["id"], _id)
        self.assertEqual(response.json()["data"]["user_name"], User.objects.first().auth_user.username)

    def test_get_user_by_id_fail(self):
        """
        Get a user by ID that does not exist
        """

        # Create user
        self.test_create_user()

        # Get user
        response = self.client.get(reverse("user_by_id", kwargs={"_id": 12345}))

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json()["ok"])
