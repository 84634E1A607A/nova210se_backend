"""
Dispatches the message to the appropriate handler function.
"""
from main.ws import MainWebsocketConsumer


async def dispatch_message(self: MainWebsocketConsumer, message: dict):
    try:
        await self.send_ok(message["action"], message["data"], 0)
    except Exception as e:
        await self.send_error(f"Internal server error: {e}", 0, 500)
