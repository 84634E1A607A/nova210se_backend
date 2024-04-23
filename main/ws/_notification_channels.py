"""
Describes multiple channels that a user may subscribe to

- User notification channel (user_{user_id}), used to notify user of account changes / friend changes etc
- Private chat channel (private_chat_{user_id}), used to notify user of private chat messages
- Chat channel (chat_{chat_id}), used to notify chat members of group chat messages / admin info / etc
- Session channel (session_{session_id}), used to notify user of session logout
"""
from channels.db import database_sync_to_async

from main.models import UserChatRelation
from main.ws import MainWebsocketConsumer


async def setup_new_socket_channel(consumer: MainWebsocketConsumer) -> None:
    """
    Setup channels to listen to for a new websocket connection
    """

    user = consumer.user
    await consumer.channel_layer.group_add(f"user_{user.id}", consumer.channel_name)
    await consumer.channel_layer.group_add(f"private_chat_{user.id}", consumer.channel_name)
    await consumer.channel_layer.group_add(f"session_{consumer.session_key}", consumer.channel_name)

    relations = await database_sync_to_async(lambda: list(UserChatRelation.objects.filter(user=user)))()

    for relation in relations:
        if await database_sync_to_async(lambda r: r.chat.is_private())(relation):
            continue

        await consumer.channel_layer.group_add(f"chat_{relation.chat.id}", consumer.channel_name)


async def discard_socket_channel(consumer: MainWebsocketConsumer) -> None:
    """
    Discard channels that the user was listening to
    """

    user = consumer.user
    await consumer.channel_layer.group_discard(f"user_{user.id}", consumer.channel_name)
    await consumer.channel_layer.group_discard(f"private_chat_{user.id}", consumer.channel_name)
    await consumer.channel_layer.group_discard(f"session_{consumer.session_key}", consumer.channel_name)

    relations = await database_sync_to_async(lambda: list(UserChatRelation.objects.filter(user=user)))()

    for relation in relations:
        if await database_sync_to_async(lambda r: r.chat.is_private())(relation):
            continue

        await consumer.channel_layer.group_discard(f"chat_{relation.chat.id}", consumer.channel_name)
