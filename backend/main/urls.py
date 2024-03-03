import main.views as views
from django.urls import path

urlpatterns = [
    path('user/login', views.login, name='login'),
]
