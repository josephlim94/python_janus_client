import asyncio
from typing import Dict, Optional, TYPE_CHECKING
import logging
import traceback

from .transport import JanusTransport
from .message_transaction import MessageTransaction

if TYPE_CHECKING:
    from .plugin_base import JanusPlugin


logger = logging.getLogger(__name__)


class PluginAttachFail(Exception):
    """Exception raised when plugin attachment fails.

    Args:
        response: The error response from Janus server.
    """

    def __init__(self, response: dict) -> None:
        super().__init__(f"Fail to attach plugin: {response['error']}")


class JanusSession:
    """Janus session for managing WebRTC connections and plugins.

    A session represents a connection to the Janus server and manages
    plugin handles and message routing.
    """

    __id: Optional[int]
    transport: JanusTransport
    __create_lock: asyncio.Lock
    created: bool

    def __init__(
        self,
        base_url: str = "",
        api_secret: Optional[str] = None,
        token: Optional[str] = None,
        transport: Optional[JanusTransport] = None,
    ) -> None:
        """Initialize a new Janus session.

        Args:
            base_url: Base URL for the Janus server.
            api_secret: Optional API secret for authentication.
            token: Optional token for authentication.
            transport: Optional custom transport instance.
        """
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

    def __str__(self) -> str:
        """Return string representation of the session."""
        return f"Session ({self.__id}) {self}"

    async def __aenter__(self) -> "JanusSession":
        """Enter async context manager and connect transport."""
        await self.transport.connect()
        return self

    async def __aexit__(self, exc_type, exc_value, exc_tb) -> None:
        """Exit async context manager and clean up resources."""
        if self.created:
            await self.destroy()
        await self.transport.disconnect()

    async def _create(self) -> None:
        if not self.transport.connected:
            await self.transport.connect()

        if not self.__id:
            self.__id = await self.transport.create_session(self)

        self.keepalive_task = asyncio.create_task(self.keepalive())
        self.created = True

    async def create(self) -> None:
        """Initialize session resources and start keepalive."""
        async with self.__create_lock:
            if not self.created:
                await self._create()
                self.created = True

    async def _destroy(self) -> None:
        try:
            message_transaction = await self.send(
                {"janus": "destroy"},
            )
            await message_transaction.get(matcher={"janus": "success"}, timeout=15)
            await message_transaction.done()
        except Exception as exception:
            logger.error(
                "".join(
                    traceback.format_exception(
                        type(exception),
                        value=exception,
                        tb=exception.__traceback__,
                    )
                )
            )

        self.keepalive_task.cancel()

        if self.__id is None:
            raise Exception("Session not properly initialized")

        await self.transport.destroy_session(self.__id)

        self.__id = None

    async def destroy(self) -> None:
        """Release session resources and stop keepalive.

        Should be called when the session is no longer needed.
        All plugins should be destroyed before calling this method.
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
        handle_id: Optional[int] = None,
    ) -> MessageTransaction:
        """Send a message through this session.

        Args:
            message: The message to send to Janus.
            handle_id: Optional plugin handle ID for plugin-specific messages.

        Returns:
            MessageTransaction for tracking the response.

        Raises:
            Exception: If session is not properly initialized.
        """
        self.__sanitize_message(message=message)

        if not self.created:
            await self.create()

        if self.__id is None:
            raise Exception("Session not properly initialized")

        return await self.transport.send(
            message,
            session_id=self.__id,
            handle_id=handle_id,
        )

    async def keepalive(self) -> None:
        """Send periodic keepalive messages to maintain the session.

        Sends keepalive messages every 30 seconds to prevent the session
        from timing out due to inactivity.
        """
        # Reference: https://janus.conf.meetecho.com/docs/rest.html
        # A Janus session is kept alive as long as there's no inactivity for 60 seconds
        while True:
            await asyncio.sleep(30)
            message_transaction = await self.send({"janus": "keepalive"})
            await message_transaction.done()

    async def on_receive(self, response: dict) -> None:
        """Handle incoming messages from Janus.

        Routes messages to the appropriate plugin handle or processes
        session-level messages.

        Args:
            response: The response message from Janus.
        """
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
        """Attach a plugin to this session.

        Creates a plugin handle on the Janus server and registers it
        with this session for message routing.

        Args:
            plugin: The plugin instance to attach.

        Returns:
            The plugin handle ID assigned by Janus.

        Raises:
            PluginAttachFail: If the plugin attachment fails.
        """

        def matcher(res):
            return res["janus"] in ["error", "success"]

        message_transaction = await self.send(
            {"janus": "attach", "plugin": plugin.name},
        )
        response = await message_transaction.get(matcher=matcher)
        await message_transaction.done()

        if response["janus"] == "error":
            raise PluginAttachFail(response=response)

        # Extract plugin handle id
        handle_id = int(response["data"]["id"])

        # Register plugin
        self.plugin_handles[handle_id] = plugin

        return handle_id

    def detach_plugin(self, plugin_handle: "JanusPlugin") -> None:
        """Remove a plugin handle from this session.

        Args:
            plugin_handle: The plugin handle to remove.

        Raises:
            KeyError: If plugin handle is not found in session.
        """
        if plugin_handle.id is None:
            raise Exception("Plugin not properly initialized")

        del self.plugin_handles[plugin_handle.id]
