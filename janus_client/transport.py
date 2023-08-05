from abc import ABC, abstractmethod
import asyncio
from typing import TYPE_CHECKING
import logging
from dataclasses import dataclass
import uuid
import json

import aiohttp

if TYPE_CHECKING:
    from .session import JanusSession

logger = logging.getLogger(__name__)


@dataclass
class JanusMessage:
    janus: str
    transaction: str


class JanusTransport(ABC):
    @abstractmethod
    def send(self):
        pass

    def receive(self):
        pass

    async def create_session(self, session: "JanusSession") -> int:
        """Create Janus Session"""

        response = await self.send(JanusMessage(janus="create"))

        # Extract session ID
        session_id = int(response["data"]["id"])

        # Register session
        self.sessions[session_id] = session

        return session_id

    # Don't call this from client object, call destroy from session instead
    def destroy_session(self, session: "JanusSession") -> None:
        del self.sessions[session.id]


class JanusTransportHTTP:
    """Janus transport through HTTP

    Manage Sessions and Transactions
    """

    connected: bool = False
    transactions: dict[str, asyncio.Queue] = dict()
    sessions: dict[int, "JanusSession"] = dict()
    api_secret: str
    token: str

    def __init__(self, uri: str, api_secret: str = None, token: str = None):
        self.uri = uri.rstrip("/")
        self.api_secret = api_secret
        self.token = token

    def __sanitize_message(self, message: dict) -> None:
        if "janus" not in message:
            raise Exception('Must set "janus" field')

        if "transaction" in message:
            logger.warn(
                f"Should not set transaction ({message['transaction']}). Overriding."
            )
            del message["transaction"]

    def __build_uri(self, session_id: int = None, handle_id: int = None) -> str:
        uri = self.uri

        if session_id:
            uri = f"{uri}/{session_id}"

            if handle_id:
                uri = f"{uri}/{handle_id}"

        return uri

    async def info(self) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.uri}/info") as response:
                return await response.json()

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
        self.transactions[transaction_id] = asyncio.Queue()
        message["transaction"] = transaction_id

        # Authentication
        if self.api_secret is not None:
            message["api_secret"] = self.api_secret
        if self.token is not None:
            message["token"] = self.token

        # Send the message
        message_json = json.dumps(message)
        logger.info(f"Send: {message_json}")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=self.__build_uri(session_id=session_id, handle_id=handle_id),
                json=message,
            ) as response:
                print("Status:", response.status)
                print("Content-type:", response.headers["content-type"])

                response.raise_for_status()

                response = await response.json()

                if "error" in response:
                    raise Exception(response)

                # There must be a transaction ID
                response_transaction_id = response["transaction"]
                await self.transactions[response_transaction_id].put(response)

        # Whenever we send a message with transaction, there must be a reply
        response = response_handler(await self.transactions[transaction_id].get())
        while not response:
            response = response_handler(await self.transactions[transaction_id].get())

        # Transaction complete, delete it
        del self.transactions[transaction_id]
        return response

    async def receive(self):
        pass

    async def create_session(self, session: "JanusSession") -> int:
        """Create Janus Session"""

        response = await self.send({"janus": "create"})

        # Extract session ID
        session_id = int(response["data"]["id"])

        # Register session
        self.sessions[session_id] = session

        return session_id

    # Don't call this from client object, call destroy from session instead
    def destroy_session(self, session_id: int) -> None:
        del self.sessions[session_id]
