from django.test import Client
from django.urls import reverse
from main.models import User


class JsonClient(Client):
    """
    Custom client for JSON requests. This client sets the default content type to application/json.
    """

    @staticmethod
    def _json_wrap(func):
        """
        Wrapper for JSON requests
        """

        def wrapper(*args, **kwargs):
            if "content_type" not in kwargs:
                kwargs["content_type"] = "application/json"

            return func(*args, **kwargs)

        return wrapper

    def __init__(self):
        super().__init__()

        # Set the default content type to JSON
        for func in ["post", "put", "patch", "delete"]:
            setattr(self, func, self._json_wrap(getattr(self, func)))


def get_user_by_name(user_name: str):
    """
    Return a User object by name
    """

    return User.objects.get(auth_user__username=user_name)


def create_user(client: JsonClient, user_name: str = "test_user", password: str = "test_password"):
    """
    Create a test user and log in
    """

    response = client.post(reverse("user_register"), {
        "user_name": user_name,
        "password": password
    })

    return response.status_code == 200


def logout_user(client: JsonClient):
    """
    Log out a test user
    """

    # Log out
    response = client.post(reverse("user_logout"), content_type="")

    return response.status_code == 200


def login_user(client: JsonClient, user_name: str = "test_user", password: str = "test_password"):
    """
    Login to a test user
    """

    # Log in
    response = client.post(reverse("user_login"), {
        "user_name": user_name,
        "password": password
    })

    data = response.json()
    return response.status_code == 200 and data["ok"]
