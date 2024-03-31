from django.db import models

from main.exceptions import FieldMissingError, FieldTypeError, ClientSideError
from main.models._user import User


class FriendInvitation(models.Model):
    """
    FriendInvitation Model, stores friend invitations
    """

    id = models.AutoField(primary_key=True)

    """
    User who sends the invitation
    """
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friend_invitation_user")

    """
    User who receives the invitation
    """
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friend_invitation_friend")

    """
    Comment of the invitation
    """
    comment = models.CharField(max_length=500)

    @staticmethod
    def validate_comment(comment: any):
        if comment is None:
            raise FieldMissingError("comment")

        if not isinstance(comment, str):
            raise FieldTypeError("comment")

        if len(comment) > 500:
            raise ClientSideError("Comment too long")

    """
    Source of the invitation, -1 for search, positive for chat group id
    """
    source = models.IntegerField()

    def to_struct(self):
        return {
            "id": self.id,
            "sender": self.sender.to_basic_struct(),
            "receiver": self.receiver.to_basic_struct(),
            "comment": self.comment,
            "source": self.source if self.source >= 0 else "search",
        }
