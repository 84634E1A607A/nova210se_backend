"""
User Control
"""

from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.http import HttpRequest

from main.views.api_utils import api, check_fields
from main.views.generate_avatar import generate_random_avatar
from main.exceptions import FieldTypeError, FieldMissingError, ClientSideError
from main.models import User, FriendGroup, Friend, AuthUser, UserChatRelation


@api(allowed_methods=["POST"], needs_auth=False)
def login(data: dict, request: HttpRequest):
    """
    POST /user/login

    Login to a user account. This API accepts a POST request with JSON content. An example of which is:
    {
        "user_name": "user",
        "password": "password"
    }

    The API returns the user information if the login is successful and will set session cookies for the user.
    A successful response looks like:
    {
        "ok": true,
        "data": {
            "id": 1,
            "user_name": "user",
            "avatar_url": "https://...",
            "email": "",
            "phone": ""
        }
    }

    If the username doesn't exist or the password is incorrect, the API returns an error message with 403 status code:
    {
        "ok": false,
        "error": "User does not exist or password is incorrect"
    }

    If user_name or password field is empty or is not string, or if the JSON is bad, API returns 400 status code.
    """

    # Validate user name
    User.validate_username(data.get("user_name"), True)

    user_name: str = data["user_name"]

    User.validate_password(data.get("password"))
    password: str = data["password"]

    # Authenticate user
    if not AuthUser.objects.filter(username=user_name).exists():
        return 403, "User does not exist or password is incorrect"

    auth_user = authenticate(username=user_name, password=password)
    if auth_user is None:
        return 403, "User does not exist or password is incorrect"

    # If there is an active session, log out the user
    if request.user.is_authenticated:
        session_key = request.session.session_key
        auth_logout(request)
        from main.ws.notification import notify_logout
        notify_logout(session_key)

    # Log user in
    auth_login(request, auth_user)

    return User.objects.get(auth_user=auth_user).to_detailed_struct()


@api(allowed_methods=["POST"], needs_auth=False)
@check_fields({
    "password": str
})
def register(data: dict, request: HttpRequest):
    """
    POST /user/register

    Register a new user account. This API accepts a POST request with JSON content. An example of which is:
    {
        "user_name": "user",
        "password": "password"
    }

    The API returns the user information if the registration is successful and will set session cookies for the user.
    A successful response looks just like a login response. A default avatar base on the user's name is generated
    and returned in `data:image/png;base64,{base64}` format in the response.

    The username should be within 32 characters and only contain `a-zA-Z0-9-_()@.` characters.

    If the username already exists, the API returns an error message with `409 Conflict` status code:
    {
        "ok": false,
        "error": "User already exists"
    }

    If user_name or password field is empty or is not string, or if the JSON is bad, API returns 400 status code.
    """

    User.validate_username(data.get("user_name"))
    user_name: str = data["user_name"]

    User.validate_password(data.get("password"))
    password: str = data["password"]

    # Create user
    auth_user = AuthUser.objects.create_user(username=user_name, password=password)
    auth_user.save()

    user = User(auth_user=auth_user, avatar_url=generate_random_avatar(user_name))
    user.save()

    # Add default friend group
    default_group = FriendGroup(user=user, name="", default=True)
    default_group.save()
    user.default_group = default_group
    user.save()

    # Log user in
    auth_login(request, auth_user)

    return user.to_detailed_struct()


@api(allowed_methods=["POST"])
def logout(request):
    """
    POST /user/logout

    This API requires a valid session cookie to be sent with the request. It logs the user out and clears the session.
    If no valid session is found, the API returns 403 status code with an error message.

    The API returns 200 status code with an empty data field if the logout is successful.
    {
        "ok": true,
        "data": null
    }
    """

    session_key = request.session.session_key

    # Log user out
    auth_logout(request)

    # Notify user of logout
    from main.ws.notification import notify_logout
    notify_logout(session_key)


@api(allowed_methods=["GET", "PATCH", "DELETE"])
def query(data: dict, request):
    """
    GET, PATCH, DELETE /user

    This API requires a valid session cookie to be sent with the request. It accepts GET, PATCH and DELETE requests.

    GET request returns the user information;
    PATCH request updates the user information;
    DELETE request deletes the user.

    API documentation for each request type is provided in their own functions.
    """

    if request.method == "GET":
        return get_user_info(request)

    if request.method == "PATCH":
        return edit_user_info(data, request)

    if request.method == "DELETE":
        return delete_user(request.user)


def get_user_info(request: HttpRequest):
    """
    GET /user

    Get the user information for the current user. Returns the same struct as the login API.
    """

    user: User = User.objects.get(auth_user=request.user)

    return user.to_detailed_struct()


def edit_user_info(data: dict, request: HttpRequest):
    """
    PATCH /user

    This API edits user information, supports partial updates. The API accepts a JSON request with the following fields:
    {
        "old_password": "old password",
        "new_password": "new password",     // Optional
        "user_name": "new user name",       // Optional
        "email": "new_email@example.com",   // Optional
        "phone": "15912345678",              // Optional
        "avatar_url": "https://..."          // Optional
    }

    old_password is required if and only if new_password, email *or* phone is present. If old_password is incorrect,
    the API returns 403 status code.

    If new_password is present, the API updates the password and the session cookies (logs the user out and back in).

    If the new password doesn't conform to the password requirements, the API returns 400 status code
    with an error message.

    If email is present, the API updates the email. If the email is longer than 100 characters, or it doesn't match
    the email format, the API returns 400 error code.

    If phone is present, the API updates the phone number. If the phone number is invalid, the API returns 400.

    If email or phone is set to "", this API accepts it.

    Username can be changed, but it must conform to the username requirements. (See register API for details)

    If the avatar_url is present, the API updates the avatar URL. If the URL is longer than 490 characters,
    or it doesn't start with http(s)://, the API returns 400 error code.

    All changes are applied if and only if all checks are passed. That is to say, if any error code is returned,
    none of the requested changes are applied.

    This API returns the user information (like login page) after the update.
    """

    user: User = User.objects.get(auth_user=request.user)

    # Check password first
    if "new_password" in data or "phone" in data or "email" in data:
        if "old_password" not in data:
            raise FieldMissingError("old_password")

        if not isinstance(data["old_password"], str):
            raise FieldTypeError("old_password")

        if not user.auth_user.check_password(data["old_password"]):
            return 403, "Old password is incorrect"

    if "new_password" in data:
        User.validate_password(data.get("new_password"))

        user.auth_user.set_password(data["new_password"])

    if "email" in data:
        User.validate_email(data.get("email"))

        user.email = data["email"]

    if "phone" in data:
        User.validate_phone(data.get("phone"))

        user.phone = data["phone"]

    if "user_name" in data:
        User.validate_username(data.get("user_name"))

        user.auth_user.username = data["user_name"]

    if "avatar_url" in data:
        User.validate_avatar_url(data.get("avatar_url"))

        if data["avatar_url"] == "":
            data["avatar_url"] = generate_random_avatar(user.auth_user.username)

        user.avatar_url = data["avatar_url"]

    # Save data only if all checks have passed
    user.save()
    user.auth_user.save()
    auth_login(request, user.auth_user)
    request.session.save()

    # Notify user of profile change
    from main.ws.notification import notify_profile_change
    notify_profile_change(user, request.session.session_key)

    return user.to_detailed_struct()


def delete_user(auth_user: AuthUser):
    """
    Delete the user logged in and log him out.
    This API returns 200 status code with an empty data field if the deletion is successful.
    """

    user: User = User.objects.get(auth_user=auth_user)

    # Notify all chats for user leaving
    from main.ws.notification import notify_chat_member_to_be_removed
    for relation in UserChatRelation.objects.filter(user=user):
        notify_chat_member_to_be_removed(relation.chat, user)

    # Notify all friends for user deletion
    from main.ws.notification import notify_friend_to_be_deleted
    for friend in Friend.objects.filter(user=user).union(Friend.objects.filter(friend=user)):
        notify_friend_to_be_deleted(friend)

    # Delete friend groups
    FriendGroup.objects.filter(user=user).delete()

    # Delete friends
    Friend.objects.filter(user=user).delete()
    Friend.objects.filter(friend=user).delete()

    # Notify user of logout
    from main.ws.notification import notify_user_deletion
    notify_user_deletion(user)

    user.auth_user.delete()
    user.delete()


@api(allowed_methods=["GET"])
def get_user_info_by_id(_id: int):
    """
    GET /user/{id}

    Get the user information by user ID. Returns the same struct as the login API.

    This API requires a valid session cookie to be sent with the request, or it will return a 403 response.

    If the user with the given ID does not exist, the API returns 404 status code with an error message.
    """

    try:
        user = User.objects.get(id=_id)
    except User.DoesNotExist:
        return 404, "User not found"

    return user.to_basic_struct()
