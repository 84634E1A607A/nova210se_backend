import main.views.friend as friend
import main.views.user as user
import main.views.friend_group as friend_group
import main.views.api_utils as api_utils
from django.urls import path, re_path

urlpatterns = [
    # User control
    path('user/login', user.login, name='user_login'),
    path('user/register', user.register, name='user_register'),
    path('user/logout', user.logout, name='user_logout'),
    path('user', user.query, name='user'),
    path('user/<int:_id>)', user.get_user_info_by_id, name='user_by_id'),

    # Friend group control
    path('friend/group/add', friend_group.add, name="friend_group_add"),
    path('friend/group/<int:group_id>', friend_group.query, name='friend_group_query'),
    path('friend/group/list', friend_group.list_groups, name='friend_group_list'),

    # Friend control
    path('friend/find', friend.find, name='friend_find'),
    path('friend/invite', friend.send_invitation, name='friend_invite'),
    path('friend/invitation', friend.list_invitation, name='friend_list_invitation'),
    path('friend/invitation/<int:invitation_id>', friend.respond_to_invitation, name='friend_respond_to_invitation'),
    path('friend', friend.list_friend, name='friend_list_friend'),
    path('friend/<int:friend_user_id>', friend.query, name='friend_query'),

    # Catch all and return 404
    re_path('.*?', api_utils.not_found, name='not_found'),
]
