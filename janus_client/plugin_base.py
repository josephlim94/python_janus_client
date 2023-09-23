import logging
from abc import ABC, abstractmethod

from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
)

from .session import JanusSession
from .message_transaction import MessageTransaction


logger = logging.getLogger(__name__)


class JanusPlugin(ABC):
    """Base class to inherit when implementing a plugin"""

    name: str = "janus.plugin.base.dummy"
    """Plugin name

    Must override to match plugin name in Janus server.
    """

    __id: str
    """Plugin handle ID. Given by Janus."""

    __session: JanusSession
    """Session instance this plugin is created from."""

    _pc: RTCPeerConnection
    """A WebRTC PeerConnection. A plugin handle is expected to have
    only 1 PC.
    """

    def __init__(self) -> None:
        self.__id = None
        self._pc = RTCPeerConnection()

    @property
    def id(self) -> int:
        return self.__id

    async def attach(self, session: JanusSession):
        if self.__id:
            raise Exception(f"Plugin already attached to session ({self.__session})")

        self.__session = session
        self.__id = await session.attach_plugin(self)

    async def destroy(self):
        """Destroy plugin handle"""

        message_transaction = await self.send({"janus": "detach"})
        await message_transaction.get()
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
        """Send raw message to plugin

        Will auto attach plugin ID to the message.

        :param message: JSON serializable dictionary to send
        :return: Synchronous reply from server
        """

        self.__sanitize_message(message=message)

        return await self.__session.send(message, handle_id=self.__id)

    @abstractmethod
    async def on_receive(self, response: dict):
        """Handle asynchronous events from Janus"""
        pass

    async def create_jsep(self, pc: RTCPeerConnection, trickle: bool = False) -> dict:
        return {
            "sdp": pc.localDescription.sdp,
            "trickle": trickle,
            "type": pc.localDescription.type,
        }

    async def on_receive_jsep(self, jsep: dict):
        if self._pc:
            if self._pc.signalingState == "closed":
                raise Exception("Received JSEP when PeerConnection is closed")

            await self._pc.setRemoteDescription(
                RTCSessionDescription(sdp=jsep["sdp"], type=jsep["type"])
            )

    async def trickle(self, sdpMLineIndex, candidate):
        """Send WebRTC candidates to Janus

        :param sdpMLineIndex: (I don't know what is this)
        :param candidate: Candidate payload. (I got it from WebRTC instance callback)
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

        # await self.send({"janus": "trickle", "candidate": candidate_payload})
        await self.send({"janus": "trickle", "candidate": candidate_payload})
        # TODO: Implement sending an array of candidates
