from django.db import models
from django.contrib.auth.models import User as AuthUser


class User(models.Model):
    """
    User Model, stores user information
    """

    user = models.OneToOneField(AuthUser, on_delete=models.CASCADE)
    id = models.AutoField(primary_key=True)
    user_name = models.CharField(max_length=100)
    avatar_url = models.CharField(max_length=500)
