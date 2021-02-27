
import asyncio
from .core import JanusClient

class JanusSession:
    def __init__(self, client: JanusClient, session_id: str):
        self.client = client
        self.session_id = session_id

    async def send(self, message, **kwargs):
        if "session_id" in message:
            raise Exception("Session ID in message must not be manually added")
        message["session_id"] = self.session_id
        return await self.client.send(message, **kwargs)

    async def destroy(self):
        message = {
            "janus": "destroy",
        }
        await self.send(message)

    async def create_plugin_handle(self, plugin_type: object):
        response = await self.send({
            "janus": "attach",
            "plugin": plugin_type.name,
        })
        return plugin_type(self, response["data"]["id"])