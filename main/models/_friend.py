from django.db import models

from main.exceptions import FieldTypeError, ClientSideError, FieldMissingError
from main.models._user import User
from main.models._friend_group import FriendGroup


class Friend(models.Model):
    """
    Friend Model, stores friend relationship
    """

    id = models.AutoField(primary_key=True)

    """
    User who possesses this friend relationship
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friend_user")

    """
    User who is friend with the user
    """
    friend = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friend_friend")

    """
    Nickname of the friend
    """
    nickname = models.CharField(max_length=100)

    @staticmethod
    def validate_nickname(nickname: any):
        if nickname is None:
            raise FieldMissingError("nickname")

        if not isinstance(nickname, str):
            raise FieldTypeError("nickname")

        if len(nickname) > 100:
            raise ClientSideError("Nickname too long")

    """
    Friend group of the friend
    """
    group = models.ForeignKey(FriendGroup, on_delete=models.CASCADE, related_name="friend_friend_group")

    def to_struct(self):
        return {
            "friend": self.friend.to_detailed_struct(),
            "nickname": self.nickname,
            "group": self.group.to_struct()
        }
