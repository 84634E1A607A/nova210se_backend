"""
Dispatches the message to the appropriate handler function.
"""
from main.ws import MainWebsocketConsumer


async def dispatch_notification(self: MainWebsocketConsumer, message: dict) -> None:
    """
    Receive all notifications and send them to the front end. For certain notifications that has side effects,
    additional actions are taken.
    """

    try:
        await self.send_ok(message["action"], message["data"], 0)
    except Exception as e:
        await self.send_error(f"Internal server error: {e}", 0, 500)
        return

    # Close socket when the current session logged out
    if message["action"] == "logout":
        await self.close()
        return

    # Change session_key when the user's profile is changed and re-subscribe to the new session channel
    if message["action"] == "profile_change":
        await self.channel_layer.group_discard(f"session_{self.session_key}", self.channel_name)
        self.session_key = message["session_key"]
        await self.channel_layer.group_add(f"session_{self.session_key}", self.channel_name)
        return

    # Subscribe to new chat when a new group chat is created
    if message["action"] == "new_group_chat":
        await self.channel_layer.group_add(f"chat_{message['chat_id']}", self.channel_name)
        return

    # Unsubscribe from chat when the current user is removed from the chat
    if message["action"] == "member_deleted" and message["data"]["user_id"] == self.user.id:
        await self.channel_layer.group_discard(f"chat_{message['chat_id']}", self.channel_name)
        return

    # Unsubscribe from chat when the chat is deleted
    if message["action"] == "chat_deleted":
        await self.channel_layer.group_discard(f"chat_{message['chat_id']}", self.channel_name)
        return
