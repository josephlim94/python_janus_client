
import asyncio
from .session import JanusSession

class JanusPlugin():
    name = "janus.plugin.base.dummy"

    def __init__(self, session: JanusSession, handle_id: str):
        self.session = session
        self.handle_id = handle_id

    async def send(self, message, **kwargs):
        if "handle_id" in message:
            raise Exception("Handle ID in message must not be manually added")
        message["handle_id"] = self.handle_id
        return await self.session.send(message, **kwargs)

    async def destroy(self):
        message = {
            "janus": "detach",
        }
        await self.send(message)