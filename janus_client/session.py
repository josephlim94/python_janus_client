
import asyncio
from .core import JanusClient

class JanusSession:
    def __init__(self, client: JanusClient, session_id: str):
        self.client = client
        self.id = session_id
        self.plugin_handles = dict()
        self.keepalive_task = asyncio.create_task(self.keepalive())

    async def destroy(self):
        message = {
            "janus": "destroy",
        }
        await self.send(message)
        self.keepalive_task.cancel()
        self.client.destroy_session(self)

    async def send(self, message, **kwargs):
        if "session_id" in message:
            raise Exception("Session ID in message must not be manually added")
        message["session_id"] = self.id
        return await self.client.send(message, **kwargs)

    async def keepalive(self):
        # Reference: https://janus.conf.meetecho.com/docs/rest.html
        # A Janus session is kept alive as long as there's no inactivity for 60 seconds
        while True:
            await asyncio.sleep(30)
            await self.send({
                "janus": "keepalive",
            })

    def handle_async_response(self, response: dict):
        if "sender" in response:
            # This is response for plugin handle
            if response["sender"] in self.plugin_handles:
                self.plugin_handles[response["sender"]].handle_async_response(response)
            else:
                print("Got response for plugin handle but handle not found. Handle ID:", response["sender"])
                print("Unhandeled response:", response)
        else:
            # This is response for self
            print("Async event for session:", response)

    async def create_plugin_handle(self, plugin_type: object):
        response = await self.send({
            "janus": "attach",
            "plugin": plugin_type.name,
        })
        plugin_handle = plugin_type(self, response["data"]["id"])
        self.plugin_handles[plugin_handle.id] = plugin_handle
        return plugin_handle

    def destroy_plugin_handle(self, plugin_handle):
        del self.plugin_handles[plugin_handle.id]