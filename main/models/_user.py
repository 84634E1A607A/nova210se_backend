import re

from django.db import models
from django.contrib.auth.models import User as AuthUser

from main.exceptions import FieldMissingError, FieldTypeError, ClientSideError


EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@([A-Za-z0-9-]+\.)+[A-Za-z0-9-]+$")
DATA_URL_REGEX = re.compile(r"^data:image/[a-zA-Z]+;base64,[a-zA-Z0-9+/=]+$")


class User(models.Model):
    """
    User Model, stores user information
    """

    auth_user = models.OneToOneField(AuthUser, on_delete=models.CASCADE)

    @staticmethod
    def validate_username(username: any):
        """
        Validates the username of the user.
        """

        if username is None:
            raise FieldMissingError("username")

        if not isinstance(username, str):
            raise FieldTypeError("username")

        if len(username) > 32:
            raise ClientSideError("Username cannot be longer than 32 characters")

        if username == "":
            raise ClientSideError("Username cannot be empty")

        if not re.match(r"^[a-zA-Z0-9\-_()@.]+$", username):
            raise ClientSideError("Only a-z A-Z 0-9 - _ ( ) @ . are allowed.")

        if AuthUser.objects.filter(username=username).exists():
            raise ClientSideError("Username already exists", code=409)

    @staticmethod
    def validate_password(password: any):
        """
        Validates the password of the user.
        """

        if password is None:
            raise FieldMissingError("password")

        if not isinstance(password, str):
            raise FieldTypeError("password")

        if len(password) < 6:
            raise ClientSideError("Password should be at least 6 characters long")

        if " " in password:
            raise ClientSideError("Password cannot contain spaces")

    id = models.AutoField(primary_key=True)

    # Allow 100KB base64 encoded image
    avatar_url = models.CharField(max_length=100000)

    @staticmethod
    def validate_avatar_url(avatar_url: any):
        """
        Validates the avatar URL. The URL can be either a data URL or a URL to an image.
        """

        if avatar_url is None:
            raise FieldMissingError("avatar_url")

        if not isinstance(avatar_url, str):
            raise FieldTypeError("avatar_url")

        if DATA_URL_REGEX.match(avatar_url) is not None:
            if len(avatar_url) > 100000:
                raise ClientSideError("Avatar size too large")

            # Accept an avatar URL
            return

        if avatar_url == "":
            return

        if len(avatar_url) > 500:
            raise ClientSideError("Avatar URL cannot be longer than 500 characters")

        if re.match(r"^https?://.+", avatar_url) is None:
            raise ClientSideError("Invalid avatar URL")

    # Allow this to be null so that there won't be an infinite loop when creating user
    default_group = models.ForeignKey("FriendGroup", on_delete=models.CASCADE,
                                      related_name="user_default_group", null=True)

    # User e-mail
    email = models.CharField(max_length=100)

    @staticmethod
    def validate_email(email: any):
        """
        Validates the email of the user.
        """

        if email is None:
            raise FieldMissingError("email")

        if not isinstance(email, str):
            raise FieldTypeError("email")

        # Accept a blank email
        if email == "":
            return

        if len(email) > 100:
            raise ClientSideError("Email too long")

        if EMAIL_REGEX.match(email) is None:
            raise ClientSideError("Invalid email format")

    # Phone number
    phone = models.CharField(max_length=20)

    @staticmethod
    def validate_phone(phone: any):
        """
        Validates the phone number of the user.
        """

        if phone is None:
            raise FieldMissingError("phone")

        if not isinstance(phone, str):
            raise FieldTypeError("phone")

        # Accept a blank phone number
        if phone == "":
            return

        if len(phone) != 11:
            raise ClientSideError("Phone number too long")

        if re.match(r"^1[0-9]+$", phone) is None:
            raise ClientSideError("Invalid phone number format")

    def to_detailed_struct(self):
        """
        Convert a User model to detailed user information JSON object.

        All fields except password hash are returned, should be used when getting user's own info or friend's info.
        """

        return {
            "id": self.id,
            "user_name": self.auth_user.username,
            "avatar_url": self.avatar_url,
            "email": self.email,
            "phone": self.phone
        }

    def to_basic_struct(self):
        """
        Convert a User model to basic user information JSON object.

        Only id, name and avatar is returned, should be used when getting other users' info without being friend.
        """
        return {
            "id": self.id,
            "user_name": self.auth_user.username,
            "avatar_url": self.avatar_url
        }
