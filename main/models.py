from django.db import models
from django.contrib.auth.models import User as AuthUser


class User(models.Model):
    """
    User Model, stores user information
    """

    auth_user = models.OneToOneField(AuthUser, on_delete=models.CASCADE)
    id = models.AutoField(primary_key=True)

    # Allow 100KB base64 encoded image
    avatar_url = models.CharField(max_length=100000)

    # Allow this to be null so that there won't be an infinite loop when creating user
    default_group = models.ForeignKey("FriendGroup", on_delete=models.CASCADE,
                                      related_name="user_default_group", null=True)


class FriendGroup(models.Model):
    """
    FriendGroup Model, stores friend groups of a user
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friend_group_user")
    id = models.AutoField(primary_key=True)
    default = models.BooleanField()
    name = models.CharField(max_length=100)


class Friend(models.Model):
    """
    Friend Model, stores friend relationship
    """

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friend_user")
    friend = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friend_friend")
    nickname = models.CharField(max_length=100)
    group = models.ForeignKey(FriendGroup, on_delete=models.CASCADE, related_name="friend_friend_group")


class FriendInvitation(models.Model):
    """
    FriendInvitation Model, stores friend invitations
    """

    id = models.AutoField(primary_key=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friend_invitation_user")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friend_invitation_friend")
    comment = models.CharField(max_length=500)
    source = models.IntegerField()
