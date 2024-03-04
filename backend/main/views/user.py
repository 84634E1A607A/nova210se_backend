"""
User Control
"""

from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User as AuthUser
from django.http import HttpRequest

from .utils import api, check_fields
from .exceptions import *
from main.models import User


@api(allowed_methods=["POST"], needs_auth=False)
@check_fields({
    "user_name": str,
    "password": str
})
def login(data, request: HttpRequest):
    """
    /user/login
    """

    user_name: str = data["user_name"]
    password: str = data["password"]

    # Check username non-empty
    if user_name == "":
        return 400, "User name cannot be empty"

    # Authenticate user
    if not AuthUser.objects.filter(username=user_name).exists():
        return 401, "User does not exist or password is incorrect"

    auth_user = authenticate(username=user_name, password=password)
    if auth_user is None:
        return 401, "User does not exist or password is incorrect"

    # Log user in
    auth_login(request, auth_user)

    return get_user_info(auth_user)


@api(allowed_methods=["POST"], needs_auth=False)
@check_fields({
    "user_name": str,
    "password": str
})
def register(data, request: HttpRequest):
    """
    /user/register
    """

    user_name: str = data["user_name"]
    password: str = data["password"]

    # Check if user already exists
    if AuthUser.objects.filter(username=user_name).exists():
        return 409, "User already exists"

    # Check username non-empty
    if user_name == "":
        return 400, "User name cannot be empty"

    # Create user
    auth_user = AuthUser.objects.create_user(username=user_name, password=password)
    auth_user.save()

    user = User(auth_user=auth_user, avatar_url="")
    user.save()

    # Log user in
    auth_login(request, auth_user)

    return get_user_info(auth_user)


@api(allowed_methods=["POST"])
def logout(request):
    """
    /user/logout
    """

    # Log user out
    auth_logout(request)


@api(allowed_methods=["GET", "PUT", "DELETE"])
def query(data, request):
    """
    /user (GET, PUT, DELETE)
    """

    if request.method == "GET":
        return get_user_info(request.user)

    if request.method == "PUT":
        return edit_user_info(data, request)

    if request.method == "DELETE":
        return delete_user(request.user)


def get_user_info(auth_user: AuthUser):
    user = User.objects.get(auth_user=auth_user)
    return {
        "id": user.id,
        "user_name": user.auth_user.username,
        "avatar_url": user.avatar_url,
    }


def edit_user_info(data, request: HttpRequest):
    """
    Edit user information, supports partial updates.
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
            return 401, "Old password is incorrect"

        user.auth_user.set_password(data["new_password"])

    if "user_name" in data:
        if not isinstance(data["user_name"], str):
            raise FieldTypeError("user_name")

        user.auth_user.username = data["user_name"]

    if "avatar_url" in data:
        if not isinstance(data["avatar_url"], str):
            raise FieldTypeError("avatar_url")

        user.avatar_url = data["avatar_url"]

    user.save()
    user.auth_user.save()
    auth_login(request, user.auth_user)

    return get_user_info(request.user)


def delete_user(auth_user: AuthUser):
    user = User.objects.get(auth_user=auth_user)
    user.auth_user.delete()
    user.delete()


@api(allowed_methods=["GET"])
def get_user_info_by_id(_id: int):
    """
    /user/{id}
    """

    try:
        user = User.objects.get(id=_id)
    except User.DoesNotExist:
        return 404, "User not found"

    return {
        "id": user.id,
        "user_name": user.auth_user.username,
        "avatar_url": user.avatar_url,
    }
