"""
User Control
"""

import django.contrib.auth as auth
from .utils import api
from .exceptions import *


@api(allowed_methods=["POST"])
def login(data):
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