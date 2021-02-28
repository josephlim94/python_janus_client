
import asyncio
from .session import JanusSession

class JanusPlugin():
    name = "janus.plugin.base.dummy"

    def __init__(self, session: JanusSession, handle_id: str):
        self.session = session
        self.id = handle_id

    async def destroy(self):
        message = {
            "janus": "detach",
        }
        await self.send(message)
        self.session.destroy_plugin_handle(self)

    async def send(self, message, **kwargs):
        if "handle_id" in message:
            raise Exception("Handle ID in message must not be manually added")
        message["handle_id"] = self.id
        return await self.session.send(message, **kwargs)

    def handle_async_response(self, response: dict):
        # This is response for self
        print(response)