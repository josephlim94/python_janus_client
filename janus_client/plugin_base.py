import logging
from abc import ABC, abstractmethod
from typing import Optional

from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCConfiguration,
)

from .session import JanusSession
from .message_transaction import MessageTransaction


logger = logging.getLogger(__name__)


class JanusPlugin(ABC):
    """Base class for implementing Janus plugins.

    Important: Each plugin instance can only hold ONE WebRTC peer connection.
    If you need multiple peer connections, create multiple plugin instances.
    Access the peer connection via the `pc` property.
    """

    name: str = "janus.plugin.base.dummy"
    """Plugin name that must match the plugin name in Janus server."""

    __id: Optional[int]
    """Plugin handle ID assigned by Janus."""

    __session: JanusSession
    """Session instance this plugin is attached to."""

    __pc: RTCPeerConnection
    """WebRTC PeerConnection for this plugin handle."""

    __pc_config: Optional[RTCConfiguration]
    """Stored configuration for recreating peer connections."""

    def __init__(
        self,
        pc_config: Optional[RTCConfiguration] = None,
    ) -> None:
        """Initialize the plugin with optional peer connection configuration.

        Args:
            pc_config: Complete RTCConfiguration object for the peer connection.
                If provided, ice_servers parameter is ignored.

        Examples:
            ```python
            config = RTCConfiguration(
                iceServers=[
                    RTCIceServer(urls='stun:stun.l.google.com:19302'),
                    RTCIceServer(
                        urls='turn:turn.example.com:3478',
                        username='user',
                        credential='pass'
                    )
                ]
            )
            plugin = MyPlugin(pc_config=config)
            ```
        """
        self.__id = None

        # Store configuration for reset_connection
        self.__pc_config = pc_config
        if pc_config is not None:
            self.__pc = RTCPeerConnection(configuration=pc_config)
        else:
            self.__pc = RTCPeerConnection()

    @property
    def id(self) -> Optional[int]:
        """Get the plugin handle ID.

        Returns:
            The plugin handle ID assigned by Janus, or None if not attached.
        """
        return self.__id

    @property
    def pc(self) -> RTCPeerConnection:
        """Get the WebRTC peer connection for this plugin."""
        return self.__pc

    @property
    def pc_config(self) -> Optional[RTCConfiguration]:
        """Get the peer connection configuration used by this plugin."""
        return self.__pc_config

    async def reset_connection(self) -> None:
        """Reset the peer connection.

        Closes the existing peer connection and creates a new one with the same
        configuration that was provided during plugin initialization.

        Warning:
            This should only be used when you need to completely restart the
            WebRTC connection. In most cases, you should create a new plugin
            instance instead of resetting the connection on an existing instance.

        Example:
            ```python
            # Close existing connection and create a new one
            await plugin.reset_connection()

            # The pc property now returns the new connection
            new_pc = plugin.pc
            ```
        """
        if self.__pc.signalingState != "closed":
            await self.__pc.close()
        self.__pc = RTCPeerConnection(configuration=self.__pc_config)

    async def attach(self, session: JanusSession) -> None:
        """Attach this plugin to a Janus session.

        Args:
            session: The JanusSession to attach this plugin to.

        Raises:
            Exception: If plugin is already attached to a session.
        """
        if self.__id:
            raise Exception(f"Plugin already attached to session ({self.__session})")

        self.__session = session
        self.__id = await session.attach_plugin(self)

    async def destroy(self) -> None:
        """Destroy the plugin handle and clean up resources."""
        message_transaction = await self.send({"janus": "detach"})
        await message_transaction.get(timeout=15)
        await message_transaction.done()
        self.__session.detach_plugin(self)

    def __sanitize_message(self, message: dict) -> None:
        if "handle_id" in message:
            logger.warn(
                f"Should not set handle_id ({message['handle_id']}). Overriding."
            )
            del message["handle_id"]

    async def send(
        self,
        message: dict,
    ) -> MessageTransaction:
        """Send a message to this plugin handle.

        Automatically attaches the plugin handle ID to the message.

        Args:
            message: JSON serializable dictionary to send to the plugin.

        Returns:
            MessageTransaction for tracking the response.

        Raises:
            Exception: If plugin is not attached to a session.
        """
        if self.__id is None:
            raise Exception("Plugin not attached to session")

        self.__sanitize_message(message=message)

        return await self.__session.send(message, handle_id=self.__id)

    @abstractmethod
    async def on_receive(self, response: dict) -> None:
        """Handle asynchronous events from Janus.

        This method must be implemented by subclasses to handle
        plugin-specific messages and events.

        Args:
            response: The response message from Janus.
        """
        pass

    async def create_jsep(self, pc: RTCPeerConnection, trickle: bool = False) -> dict:
        """Create a JSEP object from a peer connection's local description.

        Args:
            pc: The RTCPeerConnection to extract the description from.
            trickle: Whether to enable trickle ICE.

        Returns:
            A JSEP dictionary containing SDP, type, and trickle settings.
        """
        return {
            "sdp": pc.localDescription.sdp,
            "trickle": trickle,
            "type": pc.localDescription.type,
        }

    async def on_receive_jsep(self, jsep: dict) -> None:
        """Handle incoming JSEP (WebRTC signaling) messages.

        Sets the remote description on the peer connection from the
        received JSEP offer or answer.

        Args:
            jsep: The JSEP message containing SDP and type.

        Raises:
            Exception: If the peer connection is in closed state.
        """
        if self.pc.signalingState == "closed":
            raise Exception("Received JSEP when PeerConnection is closed")

        await self.pc.setRemoteDescription(
            RTCSessionDescription(sdp=jsep["sdp"], type=jsep["type"])
        )

    async def trickle(
        self, sdpMLineIndex: int, candidate: Optional[str] = None
    ) -> None:
        """Send WebRTC ICE candidates to Janus using trickle ICE.

        Args:
            sdpMLineIndex: The SDP media line index for the candidate.
            candidate: The ICE candidate string, or None to signal end of candidates.
        """
        candidate_payload = dict()
        if candidate:
            candidate_payload = {
                "sdpMLineIndex": sdpMLineIndex,
                "candidate": candidate,
            }
        else:
            # Reference: https://janus.conf.meetecho.com/docs/rest.html
            # - a null candidate or a completed JSON object to notify the end of the candidates.
            # TODO: test it
            candidate_payload = None

        await self.send({"janus": "trickle", "candidate": candidate_payload})
        # TODO: Implement sending an array of candidates
