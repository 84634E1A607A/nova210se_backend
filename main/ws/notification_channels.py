"""
Describes multiple channels that a user may subscribe to

- User notification channel (user_{user_id}), used to notify user of account changes / friend changes etc
- Private chat channel (private_chat_{user_id}), used to notify user of private chat messages
- Chat channel (chat_{chat_id}), used to notify chat members of group chat messages / admin info / etc
"""
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from main.models import User, UserChatRelation


async def setup_new_socket_channel(consumer: AsyncJsonWebsocketConsumer, user: User) -> None:
    """
    Setup channels to listen to for a new websocket connection
    """

    await consumer.channel_layer.group_add(f"user_{user.id}", consumer.channel_name)
    await consumer.channel_layer.group_add(f"private_chat_{user.id}", consumer.channel_name)

    chats = await database_sync_to_async(lambda: list(UserChatRelation.objects.filter(user=user)))()

    for chat in chats:
        if chat.chat.is_private():
            continue

        await consumer.channel_layer.group_add(f"chat_{chat.chat.id}", consumer.channel_name)


async def discard_socket_channel(consumer: AsyncJsonWebsocketConsumer, user: User) -> None:
    """
    Discard channels that the user was listening to
    """

    await consumer.channel_layer.group_discard(f"user_{user.id}", consumer.channel_name)
    await consumer.channel_layer.group_discard(f"private_chat_{user.id}", consumer.channel_name)

    chats = await database_sync_to_async(lambda: list(UserChatRelation.objects.filter(user=user)))()

    for chat in chats:
        if chat.chat.is_private():
            continue

        await consumer.channel_layer.group_discard(f"chat_{chat.chat.id}", consumer.channel_name)
