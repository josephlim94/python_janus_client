import asyncio
from typing import Dict, TYPE_CHECKING
import logging

from .transport import JanusTransport, ResponseHandlerType

if TYPE_CHECKING:
    from .plugin_base import JanusPlugin


logger = logging.getLogger(__name__)


class PluginAttachFail(Exception):
    def __init__(self, response: dict) -> None:
        super().__init__(f"Fail to attach plugin: {response['error']}")


class JanusSession:
    """Janus session instance"""

    __id: int
    transport: JanusTransport
    __create_lock: asyncio.Lock
    created: bool

    def __init__(
        self,
        base_url: str = "",
        api_secret: str = None,
        token: str = None,
        transport: JanusTransport = None,
    ):
        self.__id = None
        self.__create_lock = asyncio.Lock()
        self.created = False
        self.plugin_handles: Dict[int, JanusPlugin] = dict()

        if transport:
            self.transport = transport
        else:
            self.transport = JanusTransport.create_transport(
                base_url=base_url,
                api_secret=api_secret,
                token=token,
            )

    def __str__(self):
        return f"Session ({self.__id}) {self}"

    async def _create(self) -> None:
        if not self.transport.connected:
            await self.transport.connect()

        if not self.__id:
            self.__id = await self.transport.create_session(self)

        self.keepalive_task = asyncio.create_task(self.keepalive())
        self.created = True

    async def create(self) -> None:
        """Initialize resources"""
        async with self.__create_lock:
            if not self.created:
                await self._create()

                self.created = True

    async def _destroy(self) -> None:
        await self.send(
            {"janus": "destroy"},
            response_handler=lambda res: res if res["janus"] == "success" else None,
        )
        self.keepalive_task.cancel()
        await self.transport.destroy_session(self.__id)
        self.__id = None

    async def destroy(self) -> None:
        """Release resources

        | Should be called when you don't need the session anymore.
        | Plugins from this session should be destroyed before this.
        """
        async with self.__create_lock:
            if self.created:
                await self._destroy()

                self.created = False

    def __sanitize_message(self, message: dict) -> None:
        if "session_id" in message:
            logger.warn(
                f"Should not set session_id ({message['session_id']}). Overriding."
            )
            del message["session_id"]

    async def send(
        self,
        message: dict,
        handle_id: int = None,
        response_handler: ResponseHandlerType = lambda response: response,
    ) -> dict:
        self.__sanitize_message(message=message)

        if not self.created:
            await self.create()

        return await self.transport.send(
            message,
            session_id=self.__id,
            handle_id=handle_id,
            response_handler=response_handler,
        )

    # TODO: This is not required if using HTTP REST API, though it
    #       doesn't hurt to still send it.
    async def keepalive(self) -> None:
        # Reference: https://janus.conf.meetecho.com/docs/rest.html
        # A Janus session is kept alive as long as there's no inactivity for 60 seconds
        while True:
            await asyncio.sleep(30)
            await self.send({"janus": "keepalive"})

    async def on_receive(self, response: dict):
        if "sender" not in response:
            # This is response for self
            logger.info(f"Async event for session: {response}")
            return

        # This is response for plugin handle
        plugin_id = response["sender"]
        if plugin_id not in self.plugin_handles:
            logger.info(
                f"Got response for plugin handle but handle not found. Handle ID: {plugin_id}"
            )
            logger.info(f"Unhandeled response: {response}")
            return

        await self.plugin_handles[plugin_id].on_receive(response)

    async def attach_plugin(self, plugin: "JanusPlugin") -> int:
        """Create plugin handle for the given plugin type

        :param plugin: Plugin instance with janus_client.JanusPlugin as base class
        """

        def response_handler(res):
            if res["janus"] in ["error", "success"]:
                return res

        response = await self.send(
            {"janus": "attach", "plugin": plugin.name},
            response_handler=response_handler,
        )

        if response["janus"] == "error":
            raise PluginAttachFail(response=response)

        # Extract plugin handle id
        handle_id = int(response["data"]["id"])

        # Register plugin
        self.plugin_handles[handle_id] = plugin

        return handle_id

    def detach_plugin(self, plugin_handle: "JanusPlugin"):
        del self.plugin_handles[plugin_handle.id]
