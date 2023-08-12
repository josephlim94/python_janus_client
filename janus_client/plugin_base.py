import logging
from abc import ABC, abstractmethod

from .transport import ResponseHandlerType
from .session import JanusSession


logger = logging.getLogger(__name__)


class JanusPlugin(ABC):
    """Base class to inherit when implementing a plugin"""

    name: str = "janus.plugin.base.dummy"
    """Plugin name

    Must override to match plugin name in Janus server.
    """
    __id: str
    session: JanusSession

    def __init__(self) -> None:
        self.__id = None

    @property
    def id(self) -> int:
        return self.__id

    async def attach(self, session: JanusSession):
        if self.__id:
            raise Exception(f"Plugin already attached to session ({self.session})")

        self.session = session
        self.__id = await session.attach_plugin(self)

    async def destroy(self):
        """Destroy plugin handle"""

        await self.send({"janus": "detach"})
        self.session.detach_plugin(self)

    def __sanitize_message(self, message: dict) -> None:
        if "handle_id" in message:
            logger.warn(
                f"Should not set handle_id ({message['handle_id']}). Overriding."
            )
            del message["handle_id"]

    async def send(
        self,
        message: dict,
        response_handler: ResponseHandlerType = lambda response: response,
    ) -> dict:
        """Send raw message to plugin

        Will auto attach plugin ID to the message.

        :param message: JSON serializable dictionary to send
        :return: Synchronous reply from server
        """

        self.__sanitize_message(message=message)

        return await self.session.send(
            message, handle_id=self.__id, response_handler=response_handler
        )

    @abstractmethod
    async def on_receive(self, response: dict):
        """Handle asynchronous events from Janus
        """
        pass

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
