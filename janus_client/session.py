from __future__ import annotations
import asyncio
from typing import Dict, TYPE_CHECKING
import logging

from .core import JanusConnection, JanusMessage

if TYPE_CHECKING:
    from .plugin_base import JanusPlugin


logger = logging.getLogger(__name__)
# PluginBaseType = TypeVar("PluginBaseType", bound=JanusPlugin)


class SessionMessage(JanusMessage):
    session_id: int = None
    plugin: str = None


class JanusSession:
    """Janus session instance"""

    id: int
    connection: JanusConnection

    def __init__(
        self,
        connection: JanusConnection = None,
        uri: str = "",
        api_secret: str = None,
        token: str = None,
    ):
        self.plugin_handles: Dict[int, JanusPlugin] = dict()
        self.keepalive_task = asyncio.create_task(self.keepalive())

        if connection:
            self.connection = connection
        else:
            self.connection = JanusConnection(
                uri=uri,
                api_secret=api_secret,
                token=token,
            )

    async def __connect(self):
        if self.connection.connected:
            return

        await self.connection.connect()
        response = await self.connection.send(JanusMessage(janus="create"))
        self.id = int(response["data"]["id"])
        self.connection.attach_session(self)

    async def destroy(self):
        """Release resources

        | Should be called when you don't need the session anymore.
        | Plugins from this session should be destroyed before this.
        """

        await self.send(SessionMessage(janus="destroy"))
        self.keepalive_task.cancel()
        self.connection.destroy_session(self)

    async def send(self, message: SessionMessage) -> dict:
        if message.session_id:
            raise Exception("Session ID in message must not be manually added")

        await self.__connect()

        message.session_id = self.id
        return await self.connection.send(message)

    async def keepalive(self):
        # Reference: https://janus.conf.meetecho.com/docs/rest.html
        # A Janus session is kept alive as long as there's no inactivity for 60 seconds
        while True:
            await asyncio.sleep(30)
            await self.send(SessionMessage(janus="keepalive"))

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
        self, plugin_type: JanusPlugin
    ) -> JanusPlugin:
        """Create plugin handle for the given plugin type

        PluginBaseType = TypeVar('PluginBaseType', bound=JanusPlugin)

        :param plugin_type: Plugin type with janus_client.JanusPlugin as base class
        """

        response = await self.send(
            SessionMessage(janus="attach", plugin=plugin_type.name)
        )
        plugin_handle = plugin_type(self, response["data"]["id"])
        self.plugin_handles[plugin_handle.id] = plugin_handle
        return plugin_handle

    def destroy_plugin_handle(self, plugin_handle):
        del self.plugin_handles[plugin_handle.id]
