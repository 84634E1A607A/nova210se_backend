from django.db import models

from main.exceptions import FieldMissingError, FieldTypeError, ClientSideError
from main.models._user import User


class FriendGroup(models.Model):
    """
    FriendGroup Model, stores friend groups of a user
    """

    """
    User who possesses this friend group
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friend_group_user")

    id = models.AutoField(primary_key=True)

    """
    Whether this group is a user's default group
    """
    default = models.BooleanField()

    """
    Name of the group
    """
    name = models.CharField(max_length=100)

    @staticmethod
    def validate_name(name: any) -> None:
        """
        Validates the name of the group

        :throws FieldMissingError: If the name is missing
        :throws FieldTypeError: If the name is not a string
        :throws ClientSideError: If the name is empty or too long
        """

        if name is None:
            raise FieldMissingError("group_name")

        if not isinstance(name, str):
            raise FieldTypeError("group_name")

        if name == "":
            raise ClientSideError("Group name cannot be empty")

        if len(name) > 100:
            raise ClientSideError("Group name too long")

    def to_struct(self):
        return {
            "group_id": self.id,
            "group_name": self.name
        }
