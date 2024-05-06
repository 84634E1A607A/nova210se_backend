"""
Friend control
"""

from main.models import User, AuthUser, Friend, FriendInvitation, FriendGroup, Chat, UserChatRelation, ChatMessage
from main.views.api_utils import api, check_fields


@api(allowed_methods=["POST"])
def find(data: dict, auth_user: AuthUser):
    """
    POST /friend/find

    Find user by its ID / name. Returns a list of filtered users without the current user like:
    {
        "ok": true,
        "data": [
            {
                "id": 1,
                "user_name": "user",
                "avatar_url": "https://..."
            },
            {
                ...
            },
            ...
        ]
    }

    This api requires a valid session, or it will return a 403 response.

    Possible filters are `id` and `name_contains`. If id is provided, the API performs a precise lookup.
    If a user with the given id is found, the API will return a list with only one item;
    else the API will return an empty list. If name_contains is provided, the API performs a case-sensitive search.
    Any user with a name *containing* the given string will be returned.

    If both id and name_contains are provided, the API will *only* use id to perform the lookup.

    The current user will not be returned in the list.

    If none of the filters are provided, the API returns 400 status code.
    """

    user = User.objects.get(auth_user=auth_user)

    if "id" in data:
        if not isinstance(data["id"], int):
            return 400, "Invalid user ID"

        try:
            u = User.objects.get(id=data["id"])
        except User.DoesNotExist:
            return []

        # Do not return the current user
        if u == user:
            return []

        # Do not return a system user
        if u.system:
            return []

        return [u.to_basic_struct()]

    if "name_contains" in data:
        if not isinstance(data["name_contains"], str):
            return 400, "Invalid name_contains"

        qs = User.objects.filter(auth_user__username__contains=data["name_contains"], system=False)
        result = []
        for u in qs:
            if u == user:
                continue

            result.append(u.to_basic_struct())

        return result

    return 400, "No filter provided"


def create_friendship(user: User, invitation: FriendInvitation) -> Friend:
    """
    Create a friendship between two users.

    This function creates two Friend objects, one for each user, and returns the created friendship.

    It also creates a chat for the new friendship and sends a "friend added" message to the chat.

    Invitation object is deleted after the friendship is created.
    """

    sender = invitation.sender

    # Create the friendship
    friend: Friend = Friend.objects.create(user=user, friend=sender, nickname="", group=user.default_group)
    Friend.objects.create(user=sender, friend=user, nickname="", group=sender.default_group)
    invitation.delete()

    # Notify users of the new friendship
    from main.ws.notification import notify_friend_created
    notify_friend_created(user, sender)

    # Create a chat for the new friendship
    chat = Chat.objects.create(owner=user, name="")
    chat.members.set([user, sender])
    UserChatRelation.objects.create(user=user, chat=chat, nickname="")
    UserChatRelation.objects.create(user=sender, chat=chat, nickname="")

    # Create a "friend added" message
    msg = ChatMessage.objects.create(chat=chat, sender=User.magic_user_system(),
                                     message=f"{user.auth_user.username} added {sender.auth_user.username} as a friend")

    # Notify users of the new message
    from main.ws.notification import notify_new_message
    notify_new_message(msg)

    return friend


@api(allowed_methods=["POST"])
@check_fields({
    "id": int
})
def send_invitation(data: dict, auth_user: AuthUser):
    """
    POST /friend/invite

    Send a friend invitations to the user with the given id with the given comment.

    If a pending invitation is found from the receiver to the sender, the API will accept the invitation and return
    the created friendship; source is not validated in this case.

    This API return 200 status code with empty data field if the invitation is sent successfully.

    This API requires a valid session, or it will return 403 status code.

    id, comment and source are required fields, and 400 response is returned if any of them is missing /
    type is incorrect.

    If the requested user does not exist, the API returns 400 status code with an error message.

    If the requested user is already the online user's friend, the API returns 409 status code with an error message.

    "source" can be either "search" (of type string) or a group id (of type int, not implemented yet).
    If the source is "search". Any other value will result in a 400 response.

    Comment should be less than 500 characters, or the API will return 400 status code with an error message.
    """

    FriendInvitation.validate_comment(data.get("comment"))

    user = User.objects.get(auth_user=auth_user)

    # Check if the user exists
    try:
        friend = User.objects.get(id=data["id"])
    except User.DoesNotExist:
        return 400, "User not found"

    if friend == user:
        return 400, "Cannot invite yourself as a friend"

    # Check if the user is already a friend
    if Friend.objects.filter(user=user, friend=friend).exists():
        return 409, "User is already a friend"

    # If the user receives an invitation from the sender, accept it
    if FriendInvitation.objects.filter(sender=friend, receiver=user).exists():
        f = create_friendship(user, FriendInvitation.objects.get(sender=friend, receiver=user))
        return f.to_struct()

    # Check invitation source
    if "source" not in data:
        return 400, "Source not provided"

    # Invitation from search
    if isinstance(data["source"], str):
        if data["source"] not in ["search"]:
            return 400, "Invalid source"
        source = -1

    # Invitation from group chat
    elif isinstance(data["source"], int):
        source = data["source"]

        try:
            chat = Chat.objects.get(id=source)
        except Chat.DoesNotExist:
            return 400, "Invitation source not found"

        if user not in chat.members.all():
            return 400, "You are not a member of the source chat"

        if friend not in chat.members.all():
            return 400, "Friend is not a member of the source chat"

    else:
        return 400, "Invalid source"

    # Delete previous invitation
    FriendInvitation.objects.filter(sender=user, receiver=friend).delete()

    # Create the invitation
    invitation = FriendInvitation(sender=user, receiver=friend, comment=data["comment"], source=source)
    invitation.save()


@api(allowed_methods=["GET"])
def list_invitation(auth_user: AuthUser):
    """
    GET /friend/invitation

    List all friend invitations related to the current user.

    This API requires a valid session, or it will return 403 status code.

    A successful response returns a list of invitations:
    {
        "ok": true,
        "data": [
            {
                "id": 1,
                "sender": {
                    "id": 1,
                    "user_name": "user",
                    "avatar_url": "https://..."
                },
                "receiver": {
                    "id": 2,
                    "user_name": "user2",
                    "avatar_url": "https://..."
                },
                "comment": "Hello",
                "source": "search"
            },
            ...
        ]
    }
    """

    user = User.objects.get(auth_user=auth_user)
    invitations = FriendInvitation.objects.filter(receiver=user)

    return [i.to_struct() for i in invitations]


@api(allowed_methods=["POST", "DELETE"])
def respond_to_invitation(method: str, auth_user: AuthUser, invitation_id: int):
    """
    POST, DELETE /friend/invitation/<int:invitation_id>

    Accept / reject a friend invitation by its ID. If an invitation is accepted, this API returns friend struct of
    newly created friendship. If an invitation is rejected, this API returns empty data.

    If the invitation is not found, the API returns 400 status code.

    If an invitation was found but the receiver is not the current user, the API returns 403 status code.
    """

    user = User.objects.get(auth_user=auth_user)

    try:
        invitation = FriendInvitation.objects.get(id=invitation_id)
    except FriendInvitation.DoesNotExist:
        return 400, "Invitation not found"

    if invitation.receiver != user:
        return 403, "Forbidden"

    if method == "POST":
        friend = create_friendship(user, invitation)
        return friend.to_struct()

    elif method == "DELETE":
        invitation.delete()


@api(allowed_methods=["GET", "PATCH", "DELETE"])
def query(data: dict, method: str, auth_user: AuthUser, friend_user_id: int):
    """
    GET, PATCH, DELETE /friend/<int:friend_user_id>

    Friend related queries.

    This API requires a valid session, or it will return 403 status code.

    API documentation for each API can be found in the corresponding function.
    """

    if method == "GET":
        return get_friend_info(auth_user, friend_user_id)

    if method == "PATCH":
        return update_friend(auth_user, friend_user_id, data)

    if method == "DELETE":
        return delete_friend(auth_user, friend_user_id)


def get_friend_info(auth_user: AuthUser, friend_id):
    """
    GET /friend/<int:friend_user_id>

    Get friend information by its ID.

    If the friend is not found, the API returns 404 status code; or it returns the friend information:
    {
        "ok": true,
        "data": {
            "friend": {
                "id": 1
                "user_name": "user",
                "avatar_url": "https://..."
            },
            "nickname": "Hello",
            "group": {
                "group_id": 1,
                "group_name": "Group"
            }
        }
    }
    """

    try:
        friend = Friend.objects.get(user__auth_user=auth_user, friend__id=friend_id)
    except Friend.DoesNotExist:
        return 404, "Friend not found"

    return friend.to_struct()


def update_friend(auth_user: AuthUser, friend_id, data):
    """
    PATCH /friend/<int:friend_user_id>

    Update friend information

    If the friend is not found, the API returns 400 status code; or it checks if "nickname" or "group_id" is provided.

    If "nickname" is provided, the API tries to updates the nickname. If the "nickname" is not a string, function
    returns 400. The nickname should be less than 100 characters, or the API returns 400.

    If "group_id" is provided, the API tries to updates the group. However, if the group does not exist or does not
    belong to the user, 400 and 403 is returned respectively.

    Friend information will be updated if and only if no errors occur.

    If the update is successful, the API returns the updated friend information in the same format as the get function.
    """

    try:
        friend = Friend.objects.get(user__auth_user=auth_user, friend__id=friend_id)
    except Friend.DoesNotExist:
        return 400, "Friend not found"

    if "nickname" in data:
        Friend.validate_nickname(data["nickname"])
        friend.nickname = data["nickname"]

    if "group_id" in data:
        if not isinstance(data["group_id"], int):
            return 400, "Invalid group ID"

        try:
            group = FriendGroup.objects.get(id=data["group_id"])
        except FriendGroup.DoesNotExist:
            return 400, "Group not found"

        if group.user.auth_user != auth_user:
            return 403, "Forbidden"

        friend.group = group

    friend.save()
    return friend.to_struct()


def delete_friend(auth_user: AuthUser, friend_id):
    """
    DELETE /friend/<int:friend_user_id>

    Delete a friend

    This API returns empty data if the operation is successful; or it returns 400 status code
    if the friend is not found.
    """

    try:
        friend = Friend.objects.get(user__auth_user=auth_user, friend__id=friend_id)
    except Friend.DoesNotExist:
        return 400, "Friend not found"

    from main.ws.notification import notify_friend_to_be_deleted
    notify_friend_to_be_deleted(friend)

    # Delete related private chat; Private chat SHOULD always exist and be unique
    Chat.objects.filter(owner=friend.user, members=friend.friend, name="") \
        .union(Chat.objects.filter(owner=friend.friend, members=friend.user, name="")).first().delete()

    reverse = Friend.objects.get(user=friend.friend, friend=friend.user)
    notify_friend_to_be_deleted(reverse)
    reverse.delete()

    friend.delete()


@api(allowed_methods=["GET"])
def list_friend(auth_user: AuthUser):
    """
    GET /friend

    List all friends of the current user

    This API requires a valid session, or it will return 403 status code.

    This API returns a list of friends. Each friend struct looks like that returned by the get friend info function.
    """

    friends = Friend.objects.filter(user__auth_user=auth_user)

    return [f.to_struct() for f in friends]
