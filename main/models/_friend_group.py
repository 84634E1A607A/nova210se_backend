from django.db import models
from main.models._user import User


class FriendGroup(models.Model):
    """
    FriendGroup Model, stores friend groups of a user
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friend_group_user")
    id = models.AutoField(primary_key=True)
    default = models.BooleanField()
    name = models.CharField(max_length=100)

    def to_struct(self):
        return {
            "group_id": self.id,
            "group_name": self.name
        }
