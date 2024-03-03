import main.views.user
from django.urls import path

urlpatterns = [
    path('user/login', main.views.user.login, name='login'),
]
