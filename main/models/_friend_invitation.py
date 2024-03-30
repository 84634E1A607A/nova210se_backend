from django.db import models
from main.models._user import User


class FriendInvitation(models.Model):
    """
    FriendInvitation Model, stores friend invitations
    """

    id = models.AutoField(primary_key=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friend_invitation_user")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friend_invitation_friend")
    comment = models.CharField(max_length=500)
    source = models.IntegerField()

    def to_struct(self):
        return {
            "id": self.id,
            "sender": self.sender.to_basic_struct(),
            "receiver": self.receiver.to_basic_struct(),
            "comment": self.comment,
            "source": self.source if self.source >= 0 else "search",
        }
