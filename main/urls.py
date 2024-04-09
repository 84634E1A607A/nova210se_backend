from django.urls import path, re_path

from main.views import user, friend, friend_group, api_utils, chat

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

    # Chat control
    path('chat/new', chat.new_chat, name='chat_new'),
    path('chat/<int:chat_id>/invite', chat.invite_to_chat, name='chat_invite'),
    path('chat/<int:chat_id>/invitation/<int:user_id>', chat.respond_to_invitation, name='chat_respond_to_invitation'),
    path('chat/<int:chat_id>', chat.query_chat, name='chat_get_delete'),
    path('chat', chat.list_chats, name='chat_list'),
    path('chat/<int:chat_id>/<int:member_id>/admin', chat.set_admin, name='chat_set_admin'),
    path('chat/<int:chat_id>/set_owner', chat.set_owner, name='chat_set_owner'),
    path('chat/<int:chat_id>/<int:member_id>', chat.remove_member, name='chat_remove_member'),

    # Catch all and return 404
    re_path('.*?', api_utils.not_found, name='not_found'),
]
