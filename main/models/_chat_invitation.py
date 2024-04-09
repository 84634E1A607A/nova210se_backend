from django.db import models

from main.models import Chat, User


class ChatInvitation(models.Model):
    id = models.AutoField(primary_key=True)
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    def to_struct(self):
        return {
            "invitation_id": self.id,
            "chat_id": self.chat.id,
            "user": self.user.to_basic_struct(),
            "invited_by": self.invited_by.to_basic_struct(),
            "created_at": self.created_at.timestamp()
        }
