
import asyncio
from session import JanusSession

class JanusVideoRoomPlugin:
    name = "janus.plugin.videoroom"

    def __init__(self, session: JanusSession, plugin_id: str):
        self.session = session
        self.plugin_id = plugin_id

    async def send(self, message):
        if "handle_id" in message:
            raise Exception("Handle ID in message must not be manually added")
        message["handle_id"] = self.plugin_id
        return await self.session.send(message)

    async def destroy(self):
        message = {
            "janus": "detach",
        }
        await self.send(message)