from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING, Type, TypeVar, Dict
from .plugin_base import JanusPlugin

if TYPE_CHECKING:
    from .core import JanusClient

import logging

logger = logging.getLogger(__name__)
PluginBaseType = TypeVar("PluginBaseType", bound=JanusPlugin)


class JanusSession:
    """Janus session instance, created by JanusClient"""

    def __init__(self, client: JanusClient, session_id: int):
        self.client = client
        self.id = session_id
        self.plugin_handles: Dict[int, JanusPlugin] = dict()
        self.keepalive_task = asyncio.create_task(self.keepalive())

    async def destroy(self):
        """Release resources

        | Should be called when you don't need the session anymore.
        | Plugins from this session should be destroyed before this.
        """

        message = {
            "janus": "destroy",
        }
        await self.send(message)
        self.keepalive_task.cancel()
        self.client.destroy_session(self)

    async def send(self, message: dict) -> dict:
        if "session_id" in message:
            raise Exception("Session ID in message must not be manually added")
        message["session_id"] = self.id
        return await self.client.send(message)

    async def keepalive(self):
        # Reference: https://janus.conf.meetecho.com/docs/rest.html
        # A Janus session is kept alive as long as there's no inactivity for 60 seconds
        while True:
            await asyncio.sleep(30)
            await self.send(
                {
                    "janus": "keepalive",
                }
            )

    def handle_async_response(self, response: dict):
        if "sender" in response:
            # This is response for plugin handle
            if response["sender"] in self.plugin_handles:
                self.plugin_handles[response["sender"]].handle_async_response(response)
            else:
                logger.info(
                    f"Got response for plugin handle but handle not found. Handle ID: {response['sender']}"
                )
                logger.info(f"Unhandeled response: {response}")
        else:
            # This is response for self
            logger.info(f"Async event for session: {response}")

    async def create_plugin_handle(
        self, plugin_type: Type[PluginBaseType]
    ) -> PluginBaseType:
        """Create plugin handle for the given plugin type

        PluginBaseType = TypeVar('PluginBaseType', bound=JanusPlugin)

        :param plugin_type: Plugin type with janus_client.JanusPlugin as base class
        """

        response = await self.send(
            {
                "janus": "attach",
                "plugin": plugin_type.name,
            }
        )
        plugin_handle = plugin_type(self, response["data"]["id"])
        self.plugin_handles[plugin_handle.id] = plugin_handle
        return plugin_handle

    def destroy_plugin_handle(self, plugin_handle):
        del self.plugin_handles[plugin_handle.id]
