from django.db.models import QuerySet

from .api_utils import api, check_fields
from main.models import Chat, ChatMessage, User, AuthUser, Friend, UserChatRelation, ChatInvitation
from main.exceptions import ClientSideError


def prohibit_private_chat(chat: Chat):
    """
    Raises if the chat is a private chat.
    """

    if chat.is_private():
        raise ClientSideError("You cannot perform this action in a private chat.", code=400)


@api(allowed_methods=["POST"])
@check_fields({
    "chat_members": list
})
def new_chat(data: dict, auth_user: AuthUser):
    """
    POST /chat/new

    Create a new group chat.

    This API requires authentication.

    This API accepts a POST request with JSON content. An example of which is:
    {
        "chat_name": "chat name",
        "chat_members": [1, 2, 3]
    }

    "members" should be a list of user ids. The chat will be created with the current user as the owner,
    and the users with the given ids as members. The current user will be added to the chat as a member regardless of
    whether the user id is in the "members" list.

    Each member MUST be an existing user and a friend to the current user, or the API will return 400.

    The API returns the chat information if the chat is created successfully. A successful response looks like:
    {
        "ok": true,
        "data": {See Chat.to_struct}
    }
    """

    Chat.validate_name(data.get("chat_name"))
    chat_name: str = data["chat_name"]

    user = User.objects.get(auth_user=auth_user)

    members_id: list = data["chat_members"]
    members: set[User] = {user}

    # Check members
    for member_id in members_id:
        if not isinstance(member_id, int):
            return 400, "Member id must be an integer"

        # Skip the current user as it is already added
        if member_id == user.id:
            continue

        m = Friend.objects.filter(user=user, friend__id=member_id)
        if not m.exists():
            return 400, "Either the user does not exist or is not a friend of the current user"

        members.add(m.first().friend)

    # Create chat
    chat = Chat(name=chat_name, owner=user)
    chat.save()
    chat.members.set(members)

    # Create associated user-chat messages
    for member in members:
        UserChatRelation(user=member, chat=chat, nickname="").save()

    members_str = ", ".join([member.auth_user.username for member in members])

    # Create a "group added" message
    msg = ChatMessage.objects.create(chat=chat, sender=User.magic_user_system(),
                                     message=f"Group {chat_name} created by {auth_user.username} with {members_str}")

    # Notify all members for a new chat and the new message
    from main.ws.notification import notify_new_chat, notify_new_message
    notify_new_chat(chat)
    notify_new_message(msg)

    # Return chat information
    return chat.to_struct()


@api(allowed_methods=["POST"])
@check_fields({
    "user_id": int
})
def invite_to_chat(data: dict, chat_id: int, auth_user: AuthUser):
    """
    POST /chat/<chat_id>/invite

    Invite a user to a *group* chat.

    This API requires authentication.

    This API accepts a POST request with JSON content: { "user_id": 1 }; If the operation is successful, the API will
    return 200 status code with an empty data field.

    You can invite users only in a group chat. If the chat is a private chat, the API will return 400.

    A notification will be sent to group owner and admins for them to approve / decline the invitation, but the user
    invited WILL NOT RECEIVE A NOTIFICATION.

    The user MUST be an existing user and a friend to the current user, or the API will return 400.
    """

    user: User = User.objects.get(auth_user=auth_user)

    member_id: int = data["user_id"]

    if not isinstance(member_id, int):
        return 400, "Member id must be an integer"

    if member_id == user.id:
        return 400, "Cannot invite yourself"

    m = Friend.objects.filter(user=user, friend__id=member_id)
    if not m.exists():
        return 400, "Either the user does not exist or is not a friend of the current user"

    member: User = m.first().friend

    chat: QuerySet = Chat.objects.filter(id=chat_id)

    if not chat.exists():
        return 400, "Chat not found"

    chat: Chat = chat.first()

    prohibit_private_chat(chat)

    if user not in chat.members.all():
        return 403, "You don't have permission to invite to this chat"

    if member in chat.members.all():
        return 400, "User is already in the chat"

    # Create a chat invitation
    ChatInvitation.objects.create(chat=chat, user=member, invited_by=user)

    # TODO: Notify the group owner and admins


@api()
def list_invitation(auth_user: AuthUser, chat_id: int):
    """
    GET /chat/<chat_id>/invitation

    List all pending invitations.

    This API requires authentication.

    Current user must be the chat owner or an admin to view the invitations.

    The API will return a list of invitations in the chat, each in the format of ChatInvitation.to_struct.

    If the chat does not exist, the API will return 400.

    If the user is neither the owner nor an admin of the chat, the API will return 403.
    """

    user: User = User.objects.get(auth_user=auth_user)
    chat: QuerySet = Chat.objects.filter(id=chat_id)

    if not chat.exists():
        return 400, "Chat not found"

    chat: Chat = chat.first()

    if user != chat.owner and user not in chat.admins.all():
        return 403, "You don't have permission to view the invitations"

    return [invitation.to_struct() for invitation in ChatInvitation.objects.filter(chat=chat)]


@api(allowed_methods=["POST", "DELETE"])
def respond_to_invitation(auth_user: AuthUser, chat_id: int, user_id: int, method: str):
    """
    GET / DELETE /chat/<chat_id>/invitation/<user_id>

    Approve / Decline a chat invitation.

    This API requires authentication.

    You can only approve / decline an invitation in a group chat and as the group owner or an admin.

    A successful response will return 200 status code with an empty data field.

    If the chat does not exist, the API will return 400.

    If the user is neither the owner nor an admin of the chat, the API will return 403.

    If the invitation does not exist, the API will return 400.

    For GET request:

    User will be added to the chat, and *then* magic user #SYSTEM will send a message there.

    For DELETE request:

    The invitation will be deleted.
    """

    user: User = User.objects.get(auth_user=auth_user)
    chat: QuerySet = Chat.objects.filter(id=chat_id)

    if not chat.exists():
        return 400, "Chat not found"

    chat: Chat = chat.first()

    if user != chat.owner and user not in chat.admins.all():
        return 403, "You don't have permission to approve or decline the invitation"

    invitation: QuerySet = ChatInvitation.objects.filter(chat=chat, user__id=user_id)

    if not invitation.exists():
        return 400, "Invitation not found"

    invitation: ChatInvitation = invitation.first()

    if method == "DELETE":
        invitation.delete()
        return

    # Accept the invitation
    member: User = invitation.user
    chat.members.add(member)
    UserChatRelation.objects.create(user=member, chat=chat, nickname="")
    from main.ws.notification import notify_chat_member_added
    notify_chat_member_added(chat, member)

    # Send a system message
    msg = ChatMessage.objects.create(chat=chat, sender=User.magic_user_system(),
                                     message=f"{auth_user.username} approved " +
                                             f"{member.auth_user.username} to join the group, " +
                                             f"invited by {invitation.invited_by.auth_user.username}")

    from main.ws.notification import notify_new_message
    notify_new_message(msg)

    invitation.delete()


@api()
def list_chats(auth_user: AuthUser):
    """
    GET /chat

    List all chats of the current user.

    This API requires authentication.

    The API will return a list of chats that the current user is in.
    Each chat will be returned in the format of UserChatRelation.to_struct.
    """

    user = User.objects.get(auth_user=auth_user)

    return [relation.to_struct() for relation in UserChatRelation.objects.filter(user=user)]


@api(allowed_methods=["GET", "DELETE"])
def query_chat(chat_id: int, auth_user: AuthUser, method: str):
    """
    GET,DELETE /chat/<chat_id>

    Get chat info / Leave a chat.

    This API requires authentication.

    If the chat does not exist, the API will return 400.

    For GET request:

    This API will return the chat information, refer to UserChatRelation.to_struct.

    For DELETE request:

    You can only leave a group chat.

    The current user must be a member of the chat. The whole chat WILL BE DELETED
    if the current user is the owner of the chat.

    The chat with the given chat_id will be deleted. All chat messages will be deleted as well.
    The API returns 200 status code with an empty data field if the chat is deleted successfully.
    """

    user = User.objects.get(auth_user=auth_user)

    relation = UserChatRelation.objects.filter(user=user, chat__id=chat_id)

    if not relation.exists():
        return 400, "Chat not found"

    relation = relation.first()

    chat = relation.chat

    if method == "GET":
        return relation.to_struct()

    # DELETE from here on

    prohibit_private_chat(chat)

    # Will delete the whole chat
    if user == chat.owner:
        chat.delete()
        return

    # Else, only the user will leave the chat
    if user in chat.admins.all():
        chat.admins.remove(user)
        from main.ws.notification import notify_admin_state_change
        notify_admin_state_change(chat, user, False)

    from main.ws.notification import notify_chat_member_to_be_removed
    notify_chat_member_to_be_removed(chat, user)
    chat.members.remove(user)
    UserChatRelation.objects.filter(user=user, chat=chat).delete()

    # Post a system message
    msg = ChatMessage.objects.create(chat=chat, sender=User.magic_user_system(),
                                     message=f"{auth_user.username} left the chat")

    from main.ws.notification import notify_new_message
    notify_new_message(msg)


@api()
def get_messages(chat_id: int, auth_user: AuthUser):
    """
    GET /chat/<chat_id>/messages

    Get all messages in a chat. (TODO: paging?)

    This API requires authentication.

    If the chat does not exist, the API will return 404.

    If the user doesn't belong to the chat, the API will return 403.

    A successful response will return a list of messages in the chat, ordered by send time descendent.
    """

    user = User.objects.get(auth_user=auth_user)
    chat = Chat.objects.filter(id=chat_id)

    if not chat.exists():
        return 404, "Chat not found"

    chat = chat.first()

    if user not in chat.members.all():
        return 403, "You don't have sufficient permission to view the messages"

    return [message.to_detailed_struct() for message in ChatMessage.objects.filter(chat=chat).order_by("-send_time")]


@api(allowed_methods=["POST"])
def set_admin(data: bool, chat_id: int, member_id: int, auth_user: AuthUser):
    """
    POST /chat/<chat_id>/<member_id>/admin

    Base on data, set a user as an / not an admin of a chat.

    This API requires authentication.

    You can only set a user as an admin in a group chat.

    The current user MUST be the owner of the chat, or the API will return 403.

    The user with the given member_id will be set as / as not an admin of the chat with the given chat_id.

    The chat owner cannot be set as an admin / not an admin.

    If the user is already an admin / not an admin, the API will return 400.

    The API returns 200 status code with an empty data field if operation is successful.
    """

    if not isinstance(data, bool):
        return 400, "Data must be a boolean"

    user = User.objects.get(auth_user=auth_user)

    chat: QuerySet = Chat.objects.filter(id=chat_id)

    if not chat.exists():
        return 400, "Chat not found"

    chat: Chat = chat.first()

    prohibit_private_chat(chat)

    if chat.owner != user:
        return 403, "You don't have permission to set admin"

    member = chat.members.filter(id=member_id)

    if not member.exists():
        return 400, "Member not found"

    member = member.first()

    if member == chat.owner:
        return 400, "You cannot set admin status of the chat owner"

    is_admin = member in chat.admins.all()

    if data == is_admin:
        return 400, "Member is already an admin" if data else "Member is not an admin currently"

    if data:
        chat.admins.add(member)
    else:
        chat.admins.remove(member)

    # Notify the chat members
    from main.ws.notification import notify_admin_state_change
    notify_admin_state_change(chat, member, data)


@api(allowed_methods=["POST"])
@check_fields({
    "chat_owner": int
})
def set_owner(data: dict, chat_id: int, auth_user: AuthUser):
    """
    POST /chat/<chat_id>/set_owner

    Set a new owner of a chat.

    This API requires authentication.

    You can only transfer the owner of a group chat.

    The current user MUST be the owner of the chat, or the API will return 403.

    The user with the given user_id will be set as the new owner of the chat with the given chat_id.

    If the user was an admin, the user will be removed from the admin list.

    After the operation, the current user will be added to the admin list.

    If the user is already the owner / the user is not in the group, the API will return 400.
    """

    from main.ws.notification import notify_admin_state_change, notify_owner_state_change

    new_owner_id = data["chat_owner"]
    user = User.objects.get(auth_user=auth_user)
    chat = Chat.objects.filter(id=chat_id)

    if not chat.exists():
        return 400, "Chat not found"

    chat = chat.first()

    prohibit_private_chat(chat)

    if chat.owner != user:
        return 403, "You don't have permission to set owner of this chat"

    member = chat.members.filter(id=new_owner_id)
    if not member.exists():
        return 400, "Member not found"

    member = member.first()
    if member == chat.owner:
        return 400, "Member is already the owner"

    if member in chat.admins.all():
        chat.admins.remove(member)
        notify_admin_state_change(chat, member, False)

    chat.owner = member
    chat.save()
    notify_owner_state_change(chat)

    chat.admins.add(user)
    notify_admin_state_change(chat, user, True)


@api(allowed_methods=["DELETE"])
def remove_member(chat_id: int, member_id: int, auth_user: AuthUser):
    """
    DELETE /chat/<chat_id>/<member_id>

    Remove a member from a chat.

    Authentication is required.

    You can only remove a member from a group chat.

    You MUST be at least an admin to remove a member; You MUST be the chat owner to remove an admin.

    If the operation completes successfully, the API will return 200 with an empty data field.
    """

    user = User.objects.get(auth_user=auth_user)
    chat = Chat.objects.filter(id=chat_id)

    if not chat.exists():
        return 400, "Chat not found"

    chat = chat.first()

    prohibit_private_chat(chat)

    if chat.owner != user and user not in chat.admins.all():
        return 403, "You don't have permission to remove a member"

    member: QuerySet = chat.members.filter(id=member_id)

    if not member.exists():
        return 400, "Member not found"

    member: User = member.first()

    if member == chat.owner:
        return 403, "You don't have the permission to remove the chat owner"

    if member in chat.admins.all():
        if user != chat.owner:
            return 403, "You don't have the permission to remove an admin"

        chat.admins.remove(member)
        from main.ws.notification import notify_admin_state_change
        notify_admin_state_change(chat, member, False)

    # Notify the chat members that a member is to be removed
    from main.ws.notification import notify_chat_member_to_be_removed
    notify_chat_member_to_be_removed(chat, member)
    chat.members.remove(member)
    UserChatRelation.objects.filter(user=member, chat=chat).delete()

    # Add a system message
    msg = ChatMessage.objects.create(chat=chat, sender=User.magic_user_system(),
                                     message=f"{auth_user.username} removed {member.auth_user.username} from the group")

    from main.ws.notification import notify_new_message
    notify_new_message(msg)
