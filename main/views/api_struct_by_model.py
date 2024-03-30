"""
This file is used to convert the database models to JSON objects defined in the API documentation.
"""

from main.models import User, FriendGroup, Friend, FriendInvitation


def user_basic_struct_by_model(user: User):
    """
    Convert a User model to basic user information JSON object.

    Only id, name and avatar is returned, should be used when getting other users' info without being friend.
    """

    return {
        "id": user.id,
        "user_name": user.auth_user.username,
        "avatar_url": user.avatar_url
    }


def user_detailed_struct_by_model(user: User):
    """
    Convert a User model to detailed user information JSON object.

    All fields except password hash are returned, should be used when getting user's own info or friend's info.
    """

    return {
        "id": user.id,
        "user_name": user.auth_user.username,
        "avatar_url": user.avatar_url,
        "email": user.email,
        "phone": user.phone
    }


def friend_group_struct_by_model(group: FriendGroup):
    return {
        "group_id": group.id,
        "group_name": group.name
    }


def friend_invitation_struct_by_model(invitation: FriendInvitation):
    return {
        "id": invitation.id,
        "sender": user_basic_struct_by_model(invitation.sender),
        "receiver": user_basic_struct_by_model(invitation.receiver),
        "comment": invitation.comment,
        "source": invitation.source if invitation.source >= 0 else "search",
    }


def friend_struct_by_model(friend: Friend):
    return {
        "friend": user_detailed_struct_by_model(friend.friend),
        "nickname": friend.nickname,
        "group": friend_group_struct_by_model(friend.group)
    }
