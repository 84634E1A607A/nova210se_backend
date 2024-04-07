from django.db import models

from main.exceptions import FieldMissingError, FieldTypeError, ClientSideError
from main.models import User


class Chat(models.Model):
    """
    Chat Model, stores chat information
    """

    id = models.AutoField(primary_key=True)

    name = models.CharField(max_length=60)

    @staticmethod
    def validate_name(chat_name: any):
        if chat_name is None:
            raise FieldMissingError("name")

        if not isinstance(chat_name, str):
            raise FieldTypeError("name")

        if len(chat_name) > 60:
            raise ClientSideError("Chat name too long")

        if chat_name == "":
            raise ClientSideError("Chat name cannot be empty")

    def is_private(self):
        return self.name == ""

    """
    Owner of the chat, only one User
    """
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_owner")

    """
    Admins of the chat, none to many Users. Owner is never in this list.
    """
    admins = models.ManyToManyField(User, related_name="chat_admins")

    """
    Members of the chat, one to many Users. Owner and admins are always in this list.
    """
    members = models.ManyToManyField(User, related_name="chat_members")

    def to_struct(self):
        # Imported here to avoid circular import
        from main.models import ChatMessage

        return {
            "chat_id": self.id,
            "chat_name": self.name,
            "chat_owner": self.owner.to_basic_struct(),
            "chat_admins": [admin.to_basic_struct() for admin in self.admins.all()],
            "chat_members": [member.to_basic_struct() for member in self.members.all()],
            "last_message": ChatMessage.objects.filter(chat=self).order_by("-send_time")[0].to_basic_struct()
        }
