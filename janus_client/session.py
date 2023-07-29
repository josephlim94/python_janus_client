import asyncio
from typing import Dict, TYPE_CHECKING
import logging

from .core import JanusConnection, JanusMessage

if TYPE_CHECKING:
    from .plugin_base import JanusPlugin


logger = logging.getLogger(__name__)


class SessionMessage(JanusMessage):
    session_id: int = None
    plugin: str = None


class JanusSession:
    """Janus session instance"""

    __id: int = None
    connection: JanusConnection
    created: bool = False

    def __init__(
        self,
        connection: JanusConnection = None,
        uri: str = "",
        api_secret: str = None,
        token: str = None,
    ):
        self.plugin_handles: Dict[int, JanusPlugin] = dict()

        if connection:
            self.connection = connection
        else:
            self.connection = JanusConnection(
                uri=uri,
                api_secret=api_secret,
                token=token,
            )

    async def __connect(self):
        if not self.connection.connected:
            await self.connection.connect()

        if not self.__id:
            self.__id = await self.connection.create_session(self)

        self.keepalive_task = asyncio.create_task(self.keepalive())
        self.created = True

    @property
    def id(self) -> int:
        return self.__id

    async def destroy(self):
        """Release resources

        | Should be called when you don't need the session anymore.
        | Plugins from this session should be destroyed before this.
        """

        await self.send(SessionMessage(janus="destroy"))
        self.keepalive_task.cancel()
        self.connection.destroy_session(self)
        self.__id = None
        self.created = False

    async def send(self, message: SessionMessage) -> dict:
        if message.session_id:
            raise Exception("Session ID in message must not be manually added")

        if not self.created:
            await self.__connect()

        message.session_id = self.__id
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

    async def attach_plugin(self, plugin: "JanusPlugin") -> int:
        """Create plugin handle for the given plugin type

        :param plugin: Plugin instance with janus_client.JanusPlugin as base class
        """

        response = await self.send(SessionMessage(janus="attach", plugin=plugin.name))

        # Extract plugin handle id
        handle_id = int(response["data"]["id"])

        # Register plugin
        self.plugin_handles[handle_id] = plugin

        return handle_id

    def detach_plugin(self, plugin_handle: "JanusPlugin"):
        del self.plugin_handles[plugin_handle.id]
