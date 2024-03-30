"""
Friend group control
"""

from main.models import User, AuthUser, FriendGroup
from main.views.api_utils import api, check_fields


@api(allowed_methods=["POST"])
@check_fields({
    "group_name": str
})
def add(data, auth_user: AuthUser):
    """
    POST /friend/group/add

    Add a new friend group. This API accepts a POST request with JSON content. An example of which is:
    {
        "group_name": "group name"
    }

    This API requires a valid user session, or it will return 403 status code.

    The API returns the group information if the group is created successfully.
    A successful response looks like the following JSON. Every user has a default group with empty name ("").
    {
        "ok": true,
        "data": {
            "group_id": 1,
            "group_name": "group name"
        }
    }

    If the group_name field is empty or is not string, or if its length exceeds 99 chars, API returns 400 status code.
    """

    user = User.objects.get(auth_user=auth_user)

    if data["group_name"] == "":
        return 400, "Group name cannot be empty"

    if len(data["group_name"]) > 99:
        return 400, "Group name too long"

    # Create the group
    group = FriendGroup(user=user, name=data["group_name"], default=False)
    group.save()

    return group.to_struct()


@api(allowed_methods=["GET", "PATCH", "DELETE"])
def query(data, method: str, auth_user: AuthUser, group_id: int):
    """
    GET, PATCH, DELETE /friend/group/<int:group_id>

    This API requires a valid user session, or it will return 403 status code.

    GET request returns the group information.
    PATCH request updates the group name and returns the group information.
    DELETE request deletes the group.

    Detailed API documentation for each of them can be found in the corresponding function.
    """

    if method == "GET":
        return get_info_by_id(auth_user, group_id)

    if method == "PATCH":
        return edit(data, auth_user=auth_user, group_id=group_id)

    if method == "DELETE":
        return delete(auth_user, group_id)


def get_info_by_id(auth_user: AuthUser, group_id: int):
    """
    GET /friend/group/<int:group_id>

    Returns the group information if the group is found and belongs to the user.
    A successful response looks the same as that of the add function.

    If the group is not found, the API returns 404 status code.

    If the group does not belong to the user, the API returns 403 status code.
    """

    try:
        group = FriendGroup.objects.get(id=group_id)
    except FriendGroup.DoesNotExist:
        return 404, "Group not found"

    # Check if the group belongs to the user
    if group.user.auth_user != auth_user:
        return 403, "Forbidden"

    return group.to_struct()


@check_fields({
    "group_name": str
})
def edit(data, auth_user: AuthUser, group_id: int):
    """
    PATCH /friend/group/<int:group_id>

    Update the group name and returns the group information if the group is found and belongs to the user.
    A successful response looks the same as that of the add function.

    If the group is not found, the API returns 400 status code.

    If the group does not belong to the user, the API returns 403 status code.

    The name of user's default group cannot be changed. If an attempt is made
    to change the name of the default group, this API will return 400 status code.
    """

    try:
        group = FriendGroup.objects.get(id=group_id)
    except FriendGroup.DoesNotExist:
        return 400, "Group not found"

    if group.user.auth_user != auth_user:
        return 403, "Forbidden"

    if group.default:
        return 400, "Cannot change name of default group"

    if data["group_name"] == "":
        return 400, "Group name cannot be empty"

    if len(data["group_name"]) > 99:
        return 400, "Group name too long"

    group.name = data["group_name"]
    group.save()

    return group.to_struct()


def delete(auth_user: AuthUser, group_id: int):
    """
    DELETE /friend/group/<int:group_id>

    Delete the group if the group is found and belongs to the user.
    This API returns 200 status code with an empty data field if the deletion is successful.
    {
        "ok": true,
        "data": null
    }

    If the group is not found, the API returns 400 status code.

    If the group does not belong to the user, the API returns 403 status code.

    The default group cannot be deleted. If an attempt is made to delete the default group,
    this API will return 400 status code.
    """

    try:
        group = FriendGroup.objects.get(id=group_id)
    except FriendGroup.DoesNotExist:
        return 400, "Group not found"

    if group.user.auth_user != auth_user:
        return 403, "Forbidden"

    if group.default:
        return 400, "Default group cannot be deleted"

    group.delete()


@api(allowed_methods=["GET"])
def list_groups(auth_user: AuthUser):
    """
    GET /friend/group/list

    Returns a list of friend groups that belong to the user.

    This API requires a valid user session, or it will return 403 status code.

    A successful response returns a list of group information. As every user has a default group,
    the list *should* contain at least one item.
    {
        "ok": true,
        "data": [
            {
                "group_id": 1,
                "group_name": "" // Default group
            },
            {
                "group_id": 4,
                "group_name": "custom_group"
            }
        ]
    }
    """

    user = User.objects.get(auth_user=auth_user)
    groups = FriendGroup.objects.filter(user=user)

    return [g.to_struct() for g in groups]
