"""
Friend control
"""

from django.contrib.auth.models import User as AuthUser
from django.http import HttpRequest

from main.models import User, Friend, FriendInvitation, FriendGroup
from main.views.api_utils import api, check_fields
from main.views.api_struct_by_model import user_struct_by_model, friend_invitation_struct_by_model, \
    friend_struct_by_model


@api(allowed_methods=["POST"])
def find(data, auth_user: AuthUser):
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
        try:
            u = User.objects.get(id=data["id"])
        except User.DoesNotExist:
            return []

        # Do not return the current user
        if u == user:
            return []

        return [user_struct_by_model(u)]

    if "name_contains" in data:
        qs = User.objects.filter(auth_user__username__contains=data["name_contains"])
        result = []
        for u in qs:
            if u == user:
                continue

            result.append(user_struct_by_model(u))

        return result

    return 400, "No filter provided"


@api(allowed_methods=["POST"])
@check_fields({
    "id": int,
    "comment": str
})
def send_invitation(data, auth_user: AuthUser):
    """
    POST /friend/invite

    Send a friend invitations to the user with the given id with the given comment.

    If a pending invitation is found from the receiver to the sender, the API will accept the invitation.

    This API return 200 status code with empty data field if the invitation is sent successfully.

    This API requires a valid session, or it will return 403 status code.

    id, comment and source are required fields, and 400 response is returned if any of them is missing /
    type is incorrect.

    If the requested user does not exist, the API returns 400 status code with an error message.

    If the requested user is already the online user's friend, the API returns 409 status code with an error message.

    "source" can be either "search" (of type string) or a group id (of type int, not implemented yet).
    If the source is "search". Any other value will result in a 400 response.
    """

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
        # Create the friendship
        Friend(user=user, friend=friend, nickname="", group=user.default_group).save()
        Friend(user=friend, friend=user, nickname="", group=friend.default_group).save()
        FriendInvitation.objects.filter(sender=friend, receiver=user).delete()
        return

    # Check invitation source
    if "source" not in data:
        return 400, "Source not provided"

    if isinstance(data["source"], str):
        if data["source"] not in ["search"]:
            return 400, "Invalid source"
        source = -1

    elif isinstance(data["source"], int):
        source = data["source"]
        return 400, f"Group invitation from {source} not implemented yet"

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
                "from": "search"
            },
            ...
        ]
    }
    """

    user = User.objects.get(auth_user=auth_user)
    invitations = FriendInvitation.objects.filter(receiver=user)

    return [friend_invitation_struct_by_model(i) for i in invitations]


@api(allowed_methods=["POST"])
def accept_invitation(auth_user: AuthUser, invitation_id: int):
    """
    POST /friend/invitation/<int:invitation_id>

    Accept a friend invitation by its ID and returns empty data.

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

    # Create the friendship
    Friend(user=user, friend=invitation.sender, nickname="", group=user.default_group).save()
    Friend(user=invitation.sender, friend=user, nickname="", group=invitation.sender.default_group).save()
    invitation.delete()


@api(allowed_methods=["GET", "PATCH", "DELETE"])
def query(data, request: HttpRequest, friend_user_id: int):
    """
    GET, PATCH, DELETE /friend/<int:friend_user_id>

    Friend related queries.

    This API requires a valid session, or it will return 403 status code.

    API documentation for each API can be found in the corresponding function.
    """

    if request.method == "GET":
        return get_friend_info(request.user, friend_user_id)

    if request.method == "PATCH":
        return update_friend(request.user, friend_user_id, data)

    if request.method == "DELETE":
        return delete_friend(request.user, friend_user_id)


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

    return friend_struct_by_model(friend)


def update_friend(auth_user: AuthUser, friend_id, data):
    """
    PATCH /friend/<int:friend_user_id>

    Update friend information

    If the friend is not found, the API returns 400 status code; or it checks if "nickname" or "group_id" is provided.

    If "nickname" is provided, the API tries to updates the nickname. If the "nickname" is not a string, function
    returns 400.

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
        if not isinstance(data["nickname"], str):
            return 400, "Invalid nickname"

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
    return friend_struct_by_model(friend)


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

    Friend.objects.get(user=friend.friend, friend=friend.user).delete()
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

    return [friend_struct_by_model(f) for f in friends]
