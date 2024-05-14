"""
Defines multiple notifications that can be sent to users
"""
from asgiref.sync import async_to_sync
from channels.layers import InMemoryChannelLayer

from main.models import User, ChatMessage, Chat, ChatInvitation, Friend


def get_channel_layer() -> InMemoryChannelLayer:
    if not hasattr(get_channel_layer, "layer"):
        from channels.layers import get_channel_layer as get_layer
        get_channel_layer.layer = get_layer()

    return get_channel_layer.layer


def notify_logout(session_key: str):
    """
    Notify user of logout
    """

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(f"session_{session_key}", {
        "action": "logout",
        "data": None,
    })


def notify_user_deletion(user: User):
    """
    Notify user of deletion, all open channels will be closed
    """

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(f"user_{user.id}", {
        "action": "logout",
        "data": None,
    })


def notify_profile_change(user: User, session_key: str):
    """
    Notify user of a profile change and notify open channels of the session key change
    """

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(f"user_{user.id}", {
        "action": "profile_change",
        "data": None,
        "session_key": session_key,
    })


def notify_new_chat(chat: Chat):
    """
    Notify chat members of a new chat and notify the channel to subscribe to the new chat.

    Only effective for group chats
    """

    if chat.is_private():
        return

    channel_layer = get_channel_layer()

    # Chat channel is not yet created, so we must iterate over all members to notify them
    for u in chat.members.all():
        async_to_sync(channel_layer.group_send)(f"user_{u.id}", {
            "action": "new_group_chat",
            "data": {"chat_id": chat.id},
            "chat_id": chat.id,
        })


def notify_new_message(message: ChatMessage):
    """
    Notify user of a new message; group chat messages are sent to the chat channel
    while private messages are sent to the private chat channel
    """

    chat = message.chat
    channel_layer = get_channel_layer()
    if chat.is_private():
        for u in chat.members.all():
            async_to_sync(channel_layer.group_send)(f"user_{u.id}", {
                "action": "new_message",
                "data": {"message": message.to_detailed_struct(User.magic_user_system())},
            })

    else:
        async_to_sync(channel_layer.group_send)(f"chat_{chat.id}", {
            "action": "new_message",
            "data": {"message": message.to_detailed_struct(User.magic_user_system())},
        })


def notify_message_recalled(message: ChatMessage):
    """
    Notify chat members of a message recall
    """

    chat = message.chat
    channel_layer = get_channel_layer()
    if chat.is_private():
        for u in chat.members.all():
            async_to_sync(channel_layer.group_send)(f"user_{u.id}", {
                "action": "message_recalled",
                "data": {"message_id": message.id},
            })

    else:
        async_to_sync(channel_layer.group_send)(f"chat_{chat.id}", {
            "action": "message_recalled",
            "data": {"message_id": message.id},
        })


def notify_message_deleted(message: ChatMessage, user: User):
    """
    Notify the user of a deleted message
    """

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(f"user_{user.id}", {
        "action": "message_deleted",
        "data": {"message_id": message.id},
    })


def notify_admin_state_change(chat: Chat, user: User, is_admin: bool):
    """
    Notify chat members of a change in admin status
    """

    if chat.is_private():
        return

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(f"chat_{chat.id}", {
        "action": "admin_state_change",
        "data": {"chat_id": chat.id, "user_id": user.id, "is_admin": is_admin},
    })


def notify_owner_state_change(chat: Chat):
    """
    Notify chat members of a change in owner status
    """

    if chat.is_private():
        return

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(f"chat_{chat.id}", {
        "action": "owner_state_change",
        "data": {"chat_id": chat.id, "owner_id": chat.owner.id},
    })


def notify_chat_member_to_be_removed(chat: Chat, member: User):
    """
    Notify that a member is to be deleted from a chat
    """

    if chat.is_private():
        return

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(f"chat_{chat.id}", {
        "action": "member_deleted",
        "data": {"chat_id": chat.id, "user_id": member.id},
    })


def notify_chat_member_added(chat: Chat, member: User):
    """
    Notify that a member has been added to a chat
    """

    if chat.is_private():
        return

    channel_layer = get_channel_layer()
    # Notify the new user of the chat
    async_to_sync(channel_layer.group_send)(f"user_{member.id}", {
        "action": "new_group_chat",
        "data": {"chat_id": chat.id},
        "chat_id": chat.id,
    })

    # Then notify the chat members of the new member
    async_to_sync(channel_layer.group_send)(f"chat_{chat.id}", {
        "action": "member_added",
        "data": {"chat_id": chat.id, "user_id": member.id},
    })


def notify_chat_member_invitation(invitation: ChatInvitation):
    """
    Notify the chat owner and admins of a new chat invitation
    """

    channel_layer = get_channel_layer()
    users = list(invitation.chat.admins.all()) + [invitation.chat.owner]
    for u in users:
        async_to_sync(channel_layer.group_send)(f"user_{u.id}", {
            "action": "chat_invitation",
            "data": {"invitation": invitation.to_struct()},
        })


def notify_chat_to_be_deleted(chat: Chat):
    """
    Notify chat members that a chat is to be deleted
    """

    if chat.is_private():
        return

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(f"chat_{chat.id}", {
        "action": "chat_deleted",
        "data": {"chat": chat.to_struct(User.magic_user_system())},
        "chat_id": chat.id,
    })


def notify_friend_to_be_deleted(friendship: Friend):
    """
    Notify user that a friend is to be deleted, this is sent only to the opposite user
    """

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(f"user_{friendship.friend.id}", {
        "action": "friend_deleted",
        "data": {"friend": friendship.user.to_detailed_struct()},
    })


def notify_friend_created(user: User, friend: User):
    """
    Notify user that a user accepted a friend request
    """

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(f"user_{user.id}", {
        "action": "friend_created",
        "data": {"friend": friend.to_detailed_struct()},
    })
    async_to_sync(channel_layer.group_send)(f"user_{friend.id}", {
        "action": "friend_created",
        "data": {"friend": user.to_detailed_struct()},
    })


def notify_messages_read(user: User, chat: Chat):
    """
    Notify chat members that a user has read all messages
    """

    channel_layer = get_channel_layer()
    if chat.is_private():
        for u in chat.members.all():
            async_to_sync(channel_layer.group_send)(f"user_{u.id}", {
                "action": "messages_read",
                "data": {"chat_id": chat.id, "user_id": user.id},
            })

    else:
        async_to_sync(channel_layer.group_send)(f"chat_{chat.id}", {
            "action": "messages_read",
            "data": {"chat_id": chat.id, "user_id": user.id},
        })
