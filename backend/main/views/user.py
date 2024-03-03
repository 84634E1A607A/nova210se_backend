"""
User Control
"""

from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User as AuthUser
from .utils import api
from .exceptions import *
from main.models import User


@api(allowed_methods=["POST"])
def login(data, request):
    """
    /user/login

    expects data like:
    {
        "user_name": "NAME",
        "password": "PASSWORD"
    }
    """

    # Check data type
    if not isinstance(data["user_name"], str):
        raise DataTypeError("user_name")

    if not isinstance(data["password"], str):
        raise DataTypeError("password")

    user_name: str = data["user_name"]
    password: str = data["password"]

    # Authenticate user
    if not AuthUser.objects.filter(username=user_name).exists():
        return 401, "User does not exist or password is incorrect"

    auth_user = authenticate(username=user_name, password=password)
    if auth_user is None:
        return 401, "User does not exist or password is incorrect"

    # Log user in
    auth_login(request, auth_user)

    user = User.objects.get(user=auth_user)

    return {
        "id": user.id,
        "user_name": user.user_name,
        "avatar_url": user.avatar_url,
    }


@api(allowed_methods=["POST"])
def register(data, request):
    """
    /user/register

    expects data like:
    {
        "user_name": "NAME",
        "password": "PASSWORD"
    }
    """

    # Check data type
    if not isinstance(data["user_name"], str):
        raise DataTypeError("user_name")

    if not isinstance(data["password"], str):
        raise DataTypeError("password")

    user_name: str = data["user_name"]
    password: str = data["password"]

    # Check if user already exists
    if AuthUser.objects.filter(username=user_name).exists():
        return 409, "User already exists"

    # Create user
    auth_user = AuthUser.objects.create_user(username=user_name, password=password)
    auth_user.save()

    user = User(user=auth_user, user_name=user_name, avatar_url="")
    user.save()

    # Log user in
    auth_login(request, auth_user)

    return {
        "id": user.id,
        "user_name": user.user_name,
        "avatar_url": user.avatar_url,
    }


@api(allowed_methods=["POST"])
def logout(data, request):
    """
    /user/logout
    """

    # Log user out
    auth_logout(request)
