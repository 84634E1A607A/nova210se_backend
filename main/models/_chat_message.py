from django.db import models

from main.models import User, Chat


class ChatMessage(models.Model):
    """
    Chat Message Model, stores a single chat message
    """

    id = models.AutoField(primary_key=True)

    message = models.TextField()

    send_time = models.DateTimeField(auto_now_add=True)

    sender = models.ForeignKey(User, on_delete=models.SET(User.magic_user_deleted),
                               related_name="chat_message_sender")

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="chat_message_chat")

    read_users = models.ManyToManyField(User, related_name="chat_message_read_users")

    reply_to = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, related_name="chat_message_reply_to")

    deleted = models.BooleanField(default=False)

    deleted_users = models.ManyToManyField(User, related_name="chat_message_deleted_users")

    def to_basic_struct(self, user: User):
        return {
            "message_id": self.id,
            "chat_id": self.chat.id,
            "message": self.message,
            "send_time": self.send_time.timestamp(),
            "sender": self.sender.to_basic_struct(),
            "reply_to_id": self.reply_to.id if self.reply_to is not None else None,
            "deleted": self.deleted or user in self.deleted_users.all()
        }

    def to_detailed_struct(self, user: User):
        return {
            **self.to_basic_struct(user),
            "read_users": [user.to_basic_struct() for user in self.read_users.all()],

            # Only basic struct is returned for reply_to to prevent infinite recursion
            "reply_to": self.reply_to.to_basic_struct(user) if self.reply_to is not None else None,
            "replied_by": [m.to_basic_struct(user) for m in ChatMessage.objects.filter(reply_to=self)]
        }
