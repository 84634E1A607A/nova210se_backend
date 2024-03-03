import main.views.user
import main.views.utils
from django.urls import path, re_path

urlpatterns = [
    path('user/login', main.views.user.login, name='user_login'),
    path('user/register', main.views.user.register, name='user_register'),
    path('user/logout', main.views.user.logout, name='user_logout'),
    path('user', main.views.user.query, name='user'),
    re_path(r'^user/(?P<_id>\d+)$', main.views.user.get_user_info_by_id, name='user_by_id'),

    # Catch all and return 404
    re_path('.*?', main.views.utils.not_found, name='not_found'),
]
