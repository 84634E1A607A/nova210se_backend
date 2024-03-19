import main.views.user
import main.views.friend
import main.views.friend_group
import main.views.api_utils
from django.urls import path, re_path

urlpatterns = [
    # User control
    path('user/login', main.views.user.login, name='user_login'),
    path('user/register', main.views.user.register, name='user_register'),
    path('user/logout', main.views.user.logout, name='user_logout'),
    path('user', main.views.user.query, name='user'),
    path('user/<int:_id>)', main.views.user.get_user_info_by_id, name='user_by_id'),

    # Friend group control
    path('friend/group/add', main.views.friend_group.add, name="friend_group_add"),
    path('friend/group/<int:group_id>', main.views.friend_group.query, name='friend_group_query'),
    path('friend/group/list', main.views.friend_group.list_groups, name='friend_group_list'),

    # Friend control
    path('friend/find', main.views.friend.find, name='friend_find'),
    path('friend/invite', main.views.friend.send_invitation, name='friend_invite'),
    path('friend/invitation', main.views.friend.list_invitation, name='friend_list_invitation'),
    path('friend/invitation/<int:invitation_id>', main.views.friend.accept_invitation, name='friend_accept_invitation'),
    path('friend', main.views.friend.list_friend, name='friend_list_friend'),
    path('friend/<int:friend_user_id>', main.views.friend.query, name='friend_query'),

    # Catch all and return 404
    re_path('.*?', main.views.api_utils.not_found, name='not_found'),
]
