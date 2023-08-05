from abc import ABC, abstractmethod
import asyncio
from typing import TYPE_CHECKING
import logging
from dataclasses import dataclass
import uuid
import json

if TYPE_CHECKING:
    from .session import JanusSession

logger = logging.getLogger(__name__)


@dataclass
class JanusMessage:
    janus: str
    transaction: str


class JanusTransport(ABC):
    __transport_implementation: list[tuple] = []

    __base_url: str
    __api_secret: str
    __token: str
    __transactions: dict[str, asyncio.Queue]
    __sessions: dict[int, "JanusSession"]

    @abstractmethod
    async def info(self):
        pass

    @abstractmethod
    async def _send(self, message: dict):
        """Really sends the message and doesn't return a response"""
        pass

    def __init__(self, base_url: str, api_secret: str = None, token: str = None):
        self.__base_url = base_url.rstrip("/")
        self.__api_secret = api_secret
        self.__token = token
        self.__transactions = dict()
        self.__sessions = dict()

    @property
    def base_url(self) -> str:
        return self.__base_url

    async def put_response(self, transaction_id: int, response: dict) -> None:
        logger.info(f"Received: {response}")
        await self.__transactions[transaction_id].put(response)

    def __sanitize_message(self, message: dict) -> None:
        if "janus" not in message:
            raise Exception('Must set "janus" field')

        if "transaction" in message:
            logger.warn(
                f"Should not set transaction ({message['transaction']}). Overriding."
            )
            del message["transaction"]

    async def send(
        self,
        message: dict,
        session_id: int = None,
        handle_id: int = None,
        response_handler=lambda response: response,
    ) -> dict:
        """Send message to server

        :param message: JSON serializable dictionary to send

        :returns: Synchronous response from Janus server

        """

        self.__sanitize_message(message=message)

        # Create transaction
        transaction_id = uuid.uuid4().hex
        self.__transactions[transaction_id] = asyncio.Queue()
        message["transaction"] = transaction_id

        # Authentication
        if self.__api_secret is not None:
            message["api_secret"] = self.__api_secret
        if self.__token is not None:
            message["token"] = self.__token

        # IDs
        if session_id is not None:
            message["session_id"] = session_id
        if handle_id is not None:
            message["handle_id"] = handle_id

        # Send the message
        message_json = json.dumps(message)
        logger.info(f"Send: {message_json}")
        await self._send(message=message)

        # Whenever we send a message with transaction, there must be a reply
        response = response_handler(await self.__transactions[transaction_id].get())
        while not response:
            response = response_handler(await self.__transactions[transaction_id].get())

        # Transaction complete, delete it
        del self.__transactions[transaction_id]
        return response

    def receive(self):
        pass

    async def create_session(self, session: "JanusSession") -> int:
        """Create Janus Session"""

        response = await self.send({"janus": "create"})

        # Extract session ID
        session_id = int(response["data"]["id"])

        # Register session
        self.__sessions[session_id] = session

        return session_id

    # Don't call this from client object, call destroy from session instead
    def destroy_session(self, session_id: int) -> None:
        del self.__sessions[session_id]

    @staticmethod
    def register_transport(protocol_matcher, transport_cls: "JanusTransport"):
        JanusTransport.__transport_implementation.append(
            (protocol_matcher, transport_cls)
        )

    @staticmethod
    def create_transport(
        base_url: str, api_secret: str = None, token: str = None
    ) -> "JanusTransport":
        # Get matching results
        matching_results = []
        for transport_implementation in JanusTransport.__transport_implementation:
            protocol_matcher = transport_implementation[0]
            matching_results.append(protocol_matcher(base_url))

        total_matched = sum(map(bool, matching_results))

        # Cannot have more than 1 match
        if total_matched > 1:
            logger.info(JanusTransport.__transport_implementation)
            logger.info(matching_results)
            raise Exception("Matched to more than 1 protocol")
        elif total_matched == 0:
            logger.info(JanusTransport.__transport_implementation)
            logger.info(matching_results)
            raise Exception("No protocol matched")

        for index, result in enumerate(matching_results):
            if result:
                transport_protocol = JanusTransport.__transport_implementation[index][1]
                return transport_protocol(
                    base_url=base_url, api_secret=api_secret, token=token
                )