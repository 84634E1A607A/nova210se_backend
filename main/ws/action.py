from channels.db import database_sync_to_async

from main.models import User, Chat, ChatMessage
from main.ws import MainWebsocketConsumer


class ParseError(Exception):
    pass


async def parse_message(data: dict, user: User, req_id: int, error_func) -> tuple:
    """
    Parse a message dict and return the message, chat, user and reply_to; throws if the message is invalid
    """

    # Validate data
    if not isinstance(data, dict):
        await error_func("Invalid message", req_id)
        return False, None

    # Validate chat_id and get chat
    if "chat_id" not in data or not isinstance(data["chat_id"], int):
        await error_func("Invalid chat_id", req_id)
        return False, None

    chat_id: int = data["chat_id"]

    try:
        chat: Chat = await database_sync_to_async(Chat.objects.get)(id=chat_id)
    except Chat.DoesNotExist:
        await error_func("Invalid chat_id", req_id)
        return False, None

    if not await database_sync_to_async(lambda: user in chat.members.all())():
        await error_func("User is not a member of the chat", req_id)
        return False, None

    # Validate message
    if "content" not in data or not isinstance(data["content"], str):
        await error_func("Invalid message", req_id)
        return False, None

    message: str = data["content"]

    if message == "":
        await error_func("Message cannot be empty", req_id)
        return False, None

    # Validate reply_to and get ChatMessage
    if "reply_to" not in data:
        reply_to = None
    else:
        if not isinstance(data["reply_to"], int):
            await error_func("Invalid reply_to", req_id)
            return False, None

        try:
            reply_to = await database_sync_to_async(ChatMessage.objects.get)(id=data["reply_to"])
        except ChatMessage.DoesNotExist:
            await error_func("Invalid reply_to", req_id)
            return False, None

        if not await database_sync_to_async(lambda: reply_to.chat == chat)():
            await error_func("Invalid reply_to", req_id)
            return False, None

    return True, (message, chat, user, reply_to)


async def send_message(self: MainWebsocketConsumer, data: dict, req_id: int):
    """
    Send a message to a Chat
    """

    success, data = await parse_message(data, self.user, req_id, self.send_error)

    if not success:
        return

    message, chat, user, reply_to = data

    # Create message
    new_message = await (database_sync_to_async(ChatMessage.objects.create)
                         (message=message, sender=user, chat=chat, reply_to=reply_to))

    # Notify chat members
    from main.ws.notification import notify_new_message
    await database_sync_to_async(notify_new_message)(new_message)


def sync_mark_msg_recalled(message: ChatMessage):
    """
    Mark a message as recalled
    """

    message.deleted = True
    message.message = "Message recalled"
    message.save()


async def recall_message(self: MainWebsocketConsumer, data: dict, req_id: int):
    """
    Recall a message from a Chat
    """

    # Validate data and get ChatMessage
    if not isinstance(data, dict) or "message_id" not in data or not isinstance(data["message_id"], int):
        await self.send_error("Invalid message to recall", req_id)
        return

    message_id: int = data["message_id"]
    try:
        message: ChatMessage = await database_sync_to_async(ChatMessage.objects.get)(id=message_id)
    except ChatMessage.DoesNotExist:
        await self.send_error("Invalid message to recall", req_id)
        return

    if not await database_sync_to_async(lambda: message.sender == self.user)():
        await self.send_error("You are not the sender of the message", req_id)
        return

    # Recall message
    await database_sync_to_async(sync_mark_msg_recalled)(message)

    # Notify chat members
    from main.ws.notification import notify_message_recalled
    await database_sync_to_async(notify_message_recalled)(message)
