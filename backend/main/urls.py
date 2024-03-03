import main.views.user
from django.urls import path

urlpatterns = [
    path('user/login', main.views.user.login, name='user_login'),
    path('user/register', main.views.user.register, name='user_register'),
    path('user/logout', main.views.user.logout, name='user_logout'),
]
