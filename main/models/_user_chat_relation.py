from django.db import models

from . import ChatMessage
from ._user import User
from ._chat import Chat
from ..exceptions import FieldMissingError, FieldTypeError, ClientSideError


class UserChatRelation(models.Model):
    """
    User Chat Relation Model, stores user's chat relationship
    """

    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_chat_relation_user")

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="user_chat_relation_chat")

    """
    Nickname of the chat shown to the user.

    Nickname can be empty, when chat name should be displayed to the user.
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
    Time when the user last read the chat
    """
    unread_after = models.DateTimeField(auto_now_add=True)

    def to_struct(self):
        return {
            "chat": self.chat.to_struct(),
            "nickname": self.nickname,
            "unread_count": ChatMessage.objects.filter(chat=self.chat, send_time__gt=self.unread_after).count()
        }
