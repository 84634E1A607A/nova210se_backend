"""
User Control
"""

import re

from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token as csrf_get_token
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User as AuthUser
from django.http import HttpRequest

from .utils import api, check_fields, user_struct_by_model
from .exceptions import FieldTypeError, FieldMissingError
from main.models import User, FriendGroup, Friend


@csrf_exempt
@api(allowed_methods=["POST"], needs_auth=False)
@check_fields({
    "user_name": str,
    "password": str
})
def login(data, request: HttpRequest):
    """
    POST /user/login

    Login to a user account. This API accepts a POST request with JSON content. An example of which is:
    {
        "user_name": "user",
        "password": "password"
    }

    The API returns the user information if the login is successful and will set session cookies for the user.
    A successful response looks like:
    {
        "ok": true,
        "data": {
            "id": 1,
            "user_name": "user",
            "avatar_url": "https://..."
        }
    }

    If the username doesn't exist or the password is incorrect, the API returns an error message with 403 status code:
    {
        "ok": false,
        "error": "User does not exist or password is incorrect"
    }

    If user_name or password field is empty or is not string, or if the JSON is bad, API returns 400 status code.
    """

    user_name: str = data["user_name"]
    password: str = data["password"]

    # Check username non-empty
    if user_name == "":
        return 400, "User name cannot be empty"

    # Authenticate user
    if not AuthUser.objects.filter(username=user_name).exists():
        return 403, "User does not exist or password is incorrect"

    auth_user = authenticate(username=user_name, password=password)
    if auth_user is None:
        return 403, "User does not exist or password is incorrect"

    # Log user in
    auth_login(request, auth_user)

    # Add CSRF token
    csrf_get_token(request)

    return user_struct_by_model(User.objects.get(auth_user=auth_user))


@csrf_exempt
@api(allowed_methods=["POST"], needs_auth=False)
@check_fields({
    "user_name": str,
    "password": str
})
def register(data, request: HttpRequest):
    """
    POST /user/register

    Register a new user account. This API accepts a POST request with JSON content. An example of which is:
    {
        "user_name": "user",
        "password": "password"
    }

    The API returns the user information if the registration is successful and will set session cookies for the user.
    A successful response looks just like a login response.

    If the username already exists, the API returns an error message with `409 Conflict` status code:
    {
        "ok": false,
        "error": "User already exists"
    }

    If user_name or password field is empty or is not string, or if the JSON is bad, API returns 400 status code.
    """

    user_name: str = data["user_name"]
    password: str = data["password"]

    # Check if user already exists
    if AuthUser.objects.filter(username=user_name).exists():
        return 409, "User already exists"

    # Check username non-empty
    if user_name == "":
        return 400, "User name cannot be empty"

    if len(user_name) > 32:
        return 400, "User name cannot be longer than 32 characters"

    if not re.match(r"^[a-zA-Z0-9\-_()@.]+$", user_name):
        return 400, "Only a-z A-Z 0-9 - _ ( ) @ . are allowed."

    # Create user
    auth_user = AuthUser.objects.create_user(username=user_name, password=password)
    auth_user.save()

    user = User(auth_user=auth_user, avatar_url="")
    user.save()

    # Add default friend group
    default_group = FriendGroup(user=user, name="", default=True)
    default_group.save()
    user.default_group = default_group
    user.save()

    # Log user in
    auth_login(request, auth_user)

    csrf_get_token(request)

    return user_struct_by_model(user)


@api(allowed_methods=["POST"])
def logout(request):
    """
    POST /user/logout

    This API requires a valid session cookie to be sent with the request. It logs the user out and clears the session.
    If no valid session is found, the API returns 403 status code with an error message.

    The API returns 200 status code with an empty data field if the logout is successful.
    {
        "ok": true,
        "data": null
    }
    """

    # Log user out
    auth_logout(request)


@api(allowed_methods=["GET", "PATCH", "DELETE"])
def query(data, request):
    """
    GET, PATCH, DELETE /user

    This API requires a valid session cookie to be sent with the request. It accepts GET, PATCH and DELETE requests.

    GET request returns the user information;
    PATCH request updates the user information;
    DELETE request deletes the user.

    API documentation for each request type is provided in their own functions.
    """

    if request.method == "GET":
        return get_user_info(request)

    if request.method == "PATCH":
        return edit_user_info(data, request)

    if request.method == "DELETE":
        return delete_user(request.user)


def get_user_info(request: HttpRequest):
    """
    GET /user

    Get the user information for the current user. Returns the same struct as the login API.
    """

    user = User.objects.get(auth_user=request.user)

    csrf_get_token(request)

    return user_struct_by_model(user)


def edit_user_info(data, request: HttpRequest):
    """
    PATCH /user

    This API edits user information, supports partial updates. The API accepts a JSON request with the following fields:
    {
        "old_password": "old password",
        "new_password": "new password",     // Optional
        "avatar_url": "https://..."          // Optional
    }

    old_password is required if and only if new_password is present. If old_password is incorrect,
    the API returns 403 status code.

    If new_password is present, the API updates the password and the session cookies (logs the user out and back in).

    If the new password doesn't conform to the password requirements, the API returns 400 status code
    with an error message.

    If the avatar_url is present, the API updates the avatar URL. If the URL is longer than 490 characters,
    or it doesn't start with http(s)://, the API returns 400 error code.

    All changes are applied if and only if all checks are passed. That is to say, if any error code is returned,
    none of the requested changes are applied.

    This API returns the user information (like login page) after the update.
    """

    user = User.objects.get(auth_user=request.user)

    # Check password first
    if "new_password" in data:
        if not isinstance(data["new_password"], str):
            raise FieldTypeError("new_password")

        if "old_password" not in data:
            raise FieldMissingError("old_password")

        if not isinstance(data["old_password"], str):
            raise FieldTypeError("old_password")

        if not user.auth_user.check_password(data["old_password"]):
            return 403, "Old password is incorrect"

        # Check new password strength
        if len(data["new_password"]) < 6:
            return 400, "Password must be at least 6 characters long"

        if " " in data["new_password"]:
            return 400, "Password cannot contain spaces"

        user.auth_user.set_password(data["new_password"])

    if "avatar_url" in data:
        if not isinstance(data["avatar_url"], str):
            raise FieldTypeError("avatar_url")

        if len(data["avatar_url"]) > 490:
            return 400, "Avatar URL cannot be longer than 490 characters"

        if not re.match(r"^https?://", data["avatar_url"]):
            return 400, "Invalid avatar URL"

        user.avatar_url = data["avatar_url"]

    # Save data only if all checks have passed
    user.save()
    user.auth_user.save()
    auth_login(request, user.auth_user)

    return user_struct_by_model(user)


def delete_user(auth_user: AuthUser):
    """
    Delete the user logged in and log him out.
    This API returns 200 status code with an empty data field if the deletion is successful.
    """

    user = User.objects.get(auth_user=auth_user)

    # Delete friend groups
    FriendGroup.objects.filter(user=user).delete()

    # Delete friends
    Friend.objects.filter(user=user).delete()
    Friend.objects.filter(friend=user).delete()

    user.auth_user.delete()
    user.delete()


@api(allowed_methods=["GET"])
def get_user_info_by_id(_id: int):
    """
    GET /user/{id}

    Get the user information by user ID. Returns the same struct as the login API.

    This API requires a valid session cookie to be sent with the request, or it will return a 403 response.

    If the user with the given ID does not exist, the API returns 404 status code with an error message.
    """

    try:
        user = User.objects.get(id=_id)
    except User.DoesNotExist:
        return 404, "User not found"

    return user_struct_by_model(user)
