from abc import ABC, abstractmethod
import asyncio
from typing import TYPE_CHECKING, List, Dict
import logging

# import uuid
import json

from .message_transaction import MessageTransaction

if TYPE_CHECKING:
    from .session import JanusSession

logger = logging.getLogger(__name__)


class JanusTransport(ABC):
    """Janus transport protocol interface

    Manage Sessions and Transactions
    """

    __transport_implementation: List[tuple] = []

    __base_url: str
    __api_secret: str
    __token: str
    __message_transaction: Dict[str, MessageTransaction]
    __sessions: Dict[int, "JanusSession"]
    __connect_lock: asyncio.Lock
    connected: bool
    """Must set this property when connected or disconnected"""

    @abstractmethod
    async def _send(self, message: Dict) -> None:
        """Really sends the message. Doesn't return a response"""
        pass

    @abstractmethod
    async def _connect(self) -> None:
        pass

    @abstractmethod
    async def _disconnect(self) -> None:
        pass

    async def info(self) -> Dict:
        """Get info of Janus server. Will be overridden for HTTP."""
        message_transaction = await self.send({"janus": "info"})
        response = await message_transaction.get()
        await message_transaction.done()
        return response

    async def ping(self) -> Dict:
        message_transaction = await self.send(
            {"janus": "ping"},
            # response_handler=lambda res: res if res["janus"] == "pong" else None,
        )
        response = await message_transaction.get(matcher={"janus": "pong"}, timeout=15)
        await message_transaction.done()
        return response

    async def dispatch_session_created(self, session_id: int) -> None:
        """Override this method to get session created event"""
        pass

    async def dispatch_session_destroyed(self, session_id: int) -> None:
        """Override this method to get session destroyed event"""
        pass

    def __init__(
        self, base_url: str, api_secret: str = None, token: str = None, **kwargs: dict
    ):
        """Create connection instance

        :param base_url: Janus server address
        :param api_secret: (optional) API key for shared static secret authentication
        :param token: (optional) Token for shared token based authentication
        """

        self.__base_url = base_url.rstrip("/")
        self.__api_secret = api_secret
        self.__token = token
        self.__message_transaction = dict()
        self.__sessions = dict()
        self.__connect_lock = asyncio.Lock()
        self.connected = False

    # def __del__(self):
    #     asyncio.run(asyncio.create_task(self.disconnect()))

    @property
    def base_url(self) -> str:
        return self.__base_url

    # async def put_response(self, transaction_id: int, response: dict) -> None:
    #     logger.info(f"Received: {response}")
    #     await self.__transactions[transaction_id].put(response)

    async def connect(self) -> None:
        """Initialize resources"""
        async with self.__connect_lock:
            if not self.connected:
                await self._connect()

                self.connected = True

    async def disconnect(self) -> None:
        """Release resources"""
        async with self.__connect_lock:
            if self.connected:
                await self._disconnect()

                self.connected = False

    def __sanitize_message(self, message: Dict) -> None:
        if "janus" not in message:
            raise Exception('Must set "janus" field')

        if "transaction" in message:
            logger.warn(
                f"Should not set transaction ({message['transaction']}). Overriding."
            )
            del message["transaction"]

    async def send(
        self,
        message: Dict,
        session_id: int = None,
        handle_id: int = None,
    ) -> MessageTransaction:
        """Send message to server

        :param message: JSON serializable dictionary to send

        :returns: Synchronous response from Janus server

        """

        self.__sanitize_message(message=message)

        # Create transaction
        message_transaction = MessageTransaction()
        self.__message_transaction[message_transaction.id] = message_transaction
        message["transaction"] = message_transaction.id

        # Delete itself if done is called
        async def message_transaction_on_done():
            del self.__message_transaction[message_transaction.id]

        message_transaction.on_done = message_transaction_on_done

        # Authentication
        if self.__api_secret is not None:
            message["apisecret"] = self.__api_secret
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

        return message_transaction

    async def receive(self, response: dict) -> None:
        logger.info(f"Received: {response}")
        # First try transaction handlers
        if "transaction" in response:
            transaction_id = response["transaction"]

            if transaction_id in self.__message_transaction:
                self.__message_transaction[transaction_id].put_msg(message=response)
                return

        # If the response was not "eaten" by the transaction, then dispatch it
        if "session_id" in response:
            session_id = response["session_id"]
            # This is response for session or plugin handle
            if session_id in self.__sessions:
                await self.__sessions[session_id].on_receive(response)
            else:
                logger.warning(
                    f"Got response for session but session not found."
                    f"Session ID: {session_id} Unhandeled response: {response}"
                )
        else:
            # No handler found for response
            logger.info(f"Response dropped: {response}")

    async def create_session(self, session: "JanusSession") -> int:
        """Create Janus Session"""

        message_transaction = await self.send({"janus": "create"})
        response = await message_transaction.get()
        await message_transaction.done()

        # Extract session ID
        session_id = int(response["data"]["id"])

        # Register session
        self.__sessions[session_id] = session

        await self.dispatch_session_created(session_id=session_id)

        return session_id

    # Don't call this from client object, call destroy from session instead
    async def destroy_session(self, session_id: int) -> None:
        if session_id in self.__sessions:
            del self.__sessions[session_id]
        else:
            logger.warning(f"Session ID not found: {session_id}")

        await self.dispatch_session_destroyed(session_id=session_id)

        # Also release transport resources if this is the last session
        if len(self.__sessions) == 0:
            await self.disconnect()

    @staticmethod
    def register_transport(protocol_matcher, transport_cls: "JanusTransport") -> None:
        """
        Register transport class

        Pass in a regex matcher and it will be used to match base_url to the transport class.
        """
        JanusTransport.__transport_implementation.append(
            (protocol_matcher, transport_cls)
        )

    @staticmethod
    def create_transport(
        base_url: str, api_secret: str = None, token: str = None, config: Dict = {}
    ) -> "JanusTransport":
        """Create transport class

        JanusSession will call this to create the transport class automatically
        using base_url parameter.

        Args:
            base_url (str): _description_
            api_secret (str, optional): _description_. Defaults to None.
            token (str, optional): _description_. Defaults to None.
            config (Dict, optional): _description_. Defaults to {}.

        Raises:
            Exception: No transport class found
            Exception: More than 1 transport class found

        Returns:
            JanusTransport: Use this object to communicate with Janus server.
        """
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
                    base_url=base_url, api_secret=api_secret, token=token, **config
                )
