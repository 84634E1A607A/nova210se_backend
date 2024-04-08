"""
Unit tests for user-related APIs
"""

from main.models import User
from django.test import TestCase
from django.urls import reverse

from main.tests.utils import create_user, logout_user, JsonClient, get_user_by_name


class UserControlTests(TestCase):
    def setUp(self):
        self.client = JsonClient()

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

        self.assertTrue(create_user(self.client))

        # Log out
        response = self.client.post(reverse("user_logout"), content_type="")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(reverse("user")).status_code, 403)

    def test_logout_without_login(self):
        """
        Log out when there is no user logged in
        """

        # Log out
        response = self.client.post(reverse("user_logout"), content_type="")
        self.assertEqual(response.status_code, 403)

    def test_login_user(self):
        """
        Login to a test user
        """

        # Create user and log out
        self.assertTrue(create_user(self.client))
        self.assertTrue(logout_user(self.client))

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
        self.assertTrue(create_user(self.client))

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
        self.assertTrue(create_user(self.client))

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
        self.assertTrue(create_user(self.client))

        # Log in (no username)
        response = self.client.post(reverse("user_login"), {
            "password": "test_password"
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["ok"])

        # Log in (empty username)
        response = self.client.post(reverse("user_login"), {
            "user_name": "",
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
        self.assertTrue(create_user(self.client))

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
        self.assertTrue(create_user(self.client))

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
        self.assertTrue(create_user(self.client))

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
        self.assertTrue(create_user(self.client))

        # Modify user
        response = self.client.patch(reverse("user"), {
            "old_password": "test_password",
            "new_password": "new_password"
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.get(auth_user__username="test_user").auth_user.check_password("new_password"))

    def test_modify_user_password_fail(self):
        """
        Modify a user's password with wrong old password
        """

        # Create user
        self.assertTrue(create_user(self.client))

        # Modify user
        response = self.client.patch(reverse("user"), {
            "old_password": "wrong_password",
            "new_password": "new_password"
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.get(auth_user__username="test_user").auth_user.check_password("new_password"))

        response = self.client.patch(reverse("user"), {
            "new_password": "new_password"
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.get(auth_user__username="test_user").auth_user.check_password("new_password"))

        response = self.client.patch(reverse("user"), {
            "old_password": 1234567,
            "new_password": "new_password"
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.get(auth_user__username="test_user").auth_user.check_password("new_password"))

        self.assertTrue(User.objects.get(auth_user__username="test_user").auth_user.check_password("test_password"))

    def test_modify_user_password_too_short(self):
        """
        Modify a user's password with short password
        """

        # Create user
        self.assertTrue(create_user(self.client))

        # Modify user
        response = self.client.patch(reverse("user"), {
            "old_password": "test_password",
            "new_password": "1234"
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.get(auth_user__username="test_user").auth_user.check_password("1234"))

    def test_modify_user_password_with_whitespace(self):
        """
        Modify a user's password containing whitespace
        """

        # Create user
        self.assertTrue(create_user(self.client))

        # Modify user
        response = self.client.patch(reverse("user"), {
            "old_password": "test_password",
            "new_password": "1 2 3 4 5"
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.get(auth_user__username="test_user").auth_user.check_password("1 2 3 4 5"))

    def test_modify_user_avatar(self):
        """
        Modify a user's avatar
        """

        # Create user
        self.assertTrue(create_user(self.client))

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
        self.assertTrue(create_user(self.client))

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
        self.assertTrue(create_user(self.client))

        # Modify user
        response = self.client.patch(reverse("user"), {
            "avatar_url": "https://localhost:8000/" + "Hello" * 500
        })
        self.assertEqual(response.status_code, 400)

    def test_get_user_by_id(self):
        """
        Get a user by ID
        """

        # Create user
        self.assertTrue(create_user(self.client))

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
        self.assertTrue(create_user(self.client))

        # Get user
        response = self.client.get(reverse("user_by_id", kwargs={"_id": 12345}))

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json()["ok"])

    def test_valid_email(self):
        """
        Test action related to email
        """

        # Create user
        self.assertTrue(create_user(self.client))
        self.assertEqual(get_user_by_name("test_user").email, "")

        # Try valid email 1
        response = self.client.patch(reverse("user"), {
            "old_password": "test_password",
            "email": "test@gmail.com"
        })
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_user_by_name("test_user").email, "test@gmail.com")

        # Try invalid email 1
        response = self.client.patch(reverse("user"), {
            "old_password": "test_password",
            "email": "@gmail.com"
        })
        self.assertFalse(response.json()["ok"])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(get_user_by_name("test_user").email, "test@gmail.com")

        # Try invalid email 2
        response = self.client.patch(reverse("user"), {
            "old_password": "test_password",
            "email": "  @gmail.com"
        })
        self.assertFalse(response.json()["ok"])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(get_user_by_name("test_user").email, "test@gmail.com")

        # Try invalid email 3
        response = self.client.patch(reverse("user"), {
            "old_password": "test_password",
            "email": "abc@gma il.com"
        })
        self.assertFalse(response.json()["ok"])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(get_user_by_name("test_user").email, "test@gmail.com")

        # Try valid email 2
        response = self.client.patch(reverse("user"), {
            "old_password": "test_password",
            "email": "+-..+-.-+..++-+.-.+123asd6+.-@gmail.com"
        })
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_user_by_name("test_user").email, "+-..+-.-+..++-+.-.+123asd6+.-@gmail.com")

        # Try valid email 3
        response = self.client.patch(reverse("user"), {
            "old_password": "test_password",
            "email": "+++++++++++@gmail--.com.abc"
        })
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_user_by_name("test_user").email, "+++++++++++@gmail--.com.abc")

        # Try invalid email 4
        response = self.client.patch(reverse("user"), {
            "old_password": "test_password",
            "email": ("abc"*100)+"@gmail.com"
        })
        self.assertFalse(response.json()["ok"])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(get_user_by_name("test_user").email, "+++++++++++@gmail--.com.abc")

        # Try invalid email 5
        response = self.client.patch(reverse("user"), {
            "old_password": "test_password",
            "email": 1232123
        })
        self.assertFalse(response.json()["ok"])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(get_user_by_name("test_user").email, "+++++++++++@gmail--.com.abc")

    def test_valid_phone(self):
        """
        Test action related to phone
        """

        # Create user
        self.assertTrue(create_user(self.client))
        self.assertEqual(get_user_by_name("test_user").phone, "")

        # Try valid phone 1
        response = self.client.patch(reverse("user"), {
            "old_password": "test_password",
            "phone": "12345678910"
        })
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_user_by_name("test_user").phone, "12345678910")

        # Try invalid phone 1
        response = self.client.patch(reverse("user"), {
            "old_password": "test_password",
            "phone": "1111111111a"
        })
        self.assertFalse(response.json()["ok"])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(get_user_by_name("test_user").phone, "12345678910")

        # Try invalid phone 2
        response = self.client.patch(reverse("user"), {
            "old_password": "test_password",
            "phone": " 1111111111"
        })
        self.assertFalse(response.json()["ok"])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(get_user_by_name("test_user").phone, "12345678910")

        # Try invalid phone 3
        response = self.client.patch(reverse("user"), {
            "old_password": "test_password",
            "phone": "21111111111"
        })
        self.assertFalse(response.json()["ok"])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(get_user_by_name("test_user").phone, "12345678910")

        # Try invalid phone 4
        response = self.client.patch(reverse("user"), {
            "old_password": "test_password",
            "phone": 21111111111
        })
        self.assertFalse(response.json()["ok"])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(get_user_by_name("test_user").phone, "12345678910")

        # Try valid phone 2
        response = self.client.patch(reverse("user"), {
            "old_password": "test_password",
            "phone": "11111111111"
        })
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_user_by_name("test_user").phone, "11111111111")

    def test_system_users_cannot_be_found(self):
        """
        Test that system users cannot be found
        """

        # Create user #SYSTEM
        User.magic_user_system()

        create_user(self.client)

        # Search for user #SYSTEM
        response = self.client.post(reverse("friend_find"), {
            "name_contains": "#"
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(len(response.json()["data"]), 0)
