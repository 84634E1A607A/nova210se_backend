from django.db import models
from django.contrib.auth.models import User as AuthUser


class User(models.Model):
    """
    User Model, stores user information
    """

    auth_user = models.OneToOneField(AuthUser, on_delete=models.CASCADE)
    id = models.AutoField(primary_key=True)
    avatar_url = models.CharField(max_length=500)
