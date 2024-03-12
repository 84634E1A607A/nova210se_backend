import main.views.user
import main.views.utils
import main.views.friend_group
from django.urls import path, re_path

urlpatterns = [
    path('user/login', main.views.user.login, name='user_login'),
    path('user/register', main.views.user.register, name='user_register'),
    path('user/logout', main.views.user.logout, name='user_logout'),
    path('user', main.views.user.query, name='user'),
    path('user/<int:_id>)', main.views.user.get_user_info_by_id, name='user_by_id'),

    # Friend group control
    path('friend/group/add', main.views.friend_group.add, name="friend_group_add"),
    path('friend/group/<int:group_id>', main.views.friend_group.query, name='friend_group_query'),
    path('friend/group/list', main.views.friend_group.list_groups, name='friend_group_list'),

    # Catch all and return 404
    re_path('.*?', main.views.utils.not_found, name='not_found'),
]
