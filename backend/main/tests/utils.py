from django.urls import reverse
from main.models import User, AuthUser


def get_user_by_authuser_name(user_name: str):
    """
    Return a User object by name
    """

    return User.objects.get(auth_user=AuthUser.objects.get(username=user_name))


def create_user(client, user_name: str = "test_user", password: str = "test_password"):
    """
    Create a test user and log in
    """

    response = client.post(reverse("user_register"), {
        "user_name": user_name,
        "password": password
    }, content_type="application/json")

    return response.status_code == 200 and client.get(reverse("user")).status_code == 200


def logout_user(client):
    """
    Log out a test user
    """

    # Log out
    response = client.post(reverse("user_logout"), content_type="")

    return response.status_code == 200 and client.get(reverse("user")).status_code == 403


def login_user(client, user_name: str = "test_user", password: str = "test_password"):
    """
    Login to a test user
    """

    # Log in
    response = client.post(reverse("user_login"), {
        "user_name": user_name,
        "password": password
    }, content_type="application/json")

    data = response.json()
    return response.status_code == 200 and client.get(reverse("user")).status_code == 200 and data["ok"]
