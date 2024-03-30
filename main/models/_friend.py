from django.db import models
from main.models._user import User
from main.models._friend_group import FriendGroup


class Friend(models.Model):
    """
    Friend Model, stores friend relationship
    """

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friend_user")
    friend = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friend_friend")
    nickname = models.CharField(max_length=100)
    group = models.ForeignKey(FriendGroup, on_delete=models.CASCADE, related_name="friend_friend_group")

    def to_struct(self):
        return {
            "friend": self.friend.to_detailed_struct(),
            "nickname": self.nickname,
            "group": self.group.to_struct()
        }
