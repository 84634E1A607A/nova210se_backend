from django.db import models
from django.contrib.auth.models import User as AuthUser


class User(models.Model):
    """
    User Model, stores user information
    """

    auth_user = models.OneToOneField(AuthUser, on_delete=models.CASCADE)
    id = models.AutoField(primary_key=True)

    # Allow 100KB base64 encoded image
    avatar_url = models.CharField(max_length=100000)

    # Allow this to be null so that there won't be an infinite loop when creating user
    default_group = models.ForeignKey("FriendGroup", on_delete=models.CASCADE,
                                      related_name="user_default_group", null=True)

    # User e-mail
    email = models.CharField(max_length=100)

    # Phone number
    phone = models.CharField(max_length=20)

    def to_detailed_struct(self):
        """Convert a User model to detailed user information JSON object.

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
        """Convert a User model to basic user information JSON object.

        Only id, name and avatar is returned, should be used when getting other users' info without being friend.
        """
        return {
            "id": self.id,
            "user_name": self.auth_user.username,
            "avatar_url": self.avatar_url
        }
