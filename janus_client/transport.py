from abc import ABC, abstractmethod
import asyncio
from typing import TYPE_CHECKING, List, Dict, Callable, Optional
import logging

# import uuid
import json

from .message_transaction import MessageTransaction

if TYPE_CHECKING:
    from .session import JanusSession

logger = logging.getLogger(__name__)


class JanusTransport(ABC):
    """Janus transport protocol interface for managing sessions and transactions.

    Attributes:
        connected: Boolean indicating if the transport is currently connected.
    """

    __transport_implementation: List[tuple] = []

    __base_url: str
    __api_secret: Optional[str]
    __token: Optional[str]
    __message_transaction: Dict[str, MessageTransaction]
    __sessions: Dict[int, "JanusSession"]
    __connect_lock: asyncio.Lock
    connected: bool
    """Must set this property when connected or disconnected"""

    @abstractmethod
    async def _send(self, message: Dict) -> None:
        """Send a message to the Janus server.

        Args:
            message: JSON serializable dictionary containing the message to send.
        """
        pass

    @abstractmethod
    async def _connect(self) -> None:
        """Establish connection to the Janus server."""
        pass

    @abstractmethod
    async def _disconnect(self) -> None:
        """Close the connection to the Janus server."""
        pass

    async def info(self) -> Dict:
        """Get information about the Janus server.

        Returns:
            Dictionary containing server information including version,
            name, supported plugins, and other server details.

        Note:
            This method may be overridden by specific transport implementations
            (e.g., HTTP transport) to provide transport-specific behavior.
        """
        message_transaction = await self.send({"janus": "info"})
        response = await message_transaction.get()
        await message_transaction.done()
        return response

    async def ping(self) -> Dict:
        """Send a ping request to the Janus server.

        Returns:
            Dictionary containing the pong response from the server.

        Raises:
            asyncio.TimeoutError: If no pong response is received within 15 seconds.
        """
        message_transaction = await self.send(
            {"janus": "ping"},
            # response_handler=lambda res: res if res["janus"] == "pong" else None,
        )
        response = await message_transaction.get(matcher={"janus": "pong"}, timeout=15)
        await message_transaction.done()
        return response

    async def dispatch_session_created(self, session_id: int) -> None:
        """Handle session creation event.

        Args:
            session_id: The unique identifier of the newly created session.
        """
        pass

    async def dispatch_session_destroyed(self, session_id: int) -> None:
        """Handle session destruction event.

        Args:
            session_id: The unique identifier of the destroyed session.
        """
        pass

    def __init__(
        self,
        base_url: str,
        api_secret: Optional[str] = None,
        token: Optional[str] = None,
        **kwargs: dict,
    ):
        """Initialize a new Janus transport instance.

        Args:
            base_url: The base URL of the Janus server (e.g., 'ws://localhost:8188').
                Trailing slashes will be automatically removed.
            api_secret: Optional API secret for shared static secret authentication.
                If provided, will be included in all requests to the server.
            token: Optional token for shared token-based authentication.
                If provided, will be included in all requests to the server.
            **kwargs: Additional keyword arguments passed to transport implementations.
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
        """Establish connection to the Janus server.

        Raises:
            Exception: If connection establishment fails.
        """
        async with self.__connect_lock:
            if not self.connected:
                await self._connect()

                self.connected = True

    async def disconnect(self) -> None:
        """Close connection and release resources."""
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
        session_id: Optional[int] = None,
        handle_id: Optional[int] = None,
    ) -> MessageTransaction:
        """Send a message to the Janus server.

        Args:
            message: JSON serializable dictionary containing the message to send.
                Must include a 'janus' field specifying the message type.
            session_id: Optional session ID to include in the message for
                session-specific requests.
            handle_id: Optional handle ID to include in the message for
                plugin-specific requests.

        Returns:
            MessageTransaction object that can be used to wait for and retrieve
            the server's response to this message.

        Raises:
            Exception: If the message is missing the required 'janus' field.
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
        """Process an incoming response from the Janus server.

        Args:
            response: Dictionary containing the response from the Janus server.
        """
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
        """Create a new Janus session.

        Args:
            session: The JanusSession object to associate with the new session ID.

        Returns:
            The unique session ID assigned by the Janus server.

        Raises:
            Exception: If session creation fails or the server returns an error.
        """

        message_transaction = await self.send({"janus": "create"})
        response = await message_transaction.get()
        await message_transaction.done()

        if "janus" in response and response["janus"] != "success":
            raise Exception(
                f"Create session fail: {response['error'] if 'error' in response else '(EMPTY)'}"
            )

        # Extract session ID
        session_id = int(response["data"]["id"])

        # Register session
        self.__sessions[session_id] = session

        await self.dispatch_session_created(session_id=session_id)

        return session_id

    async def destroy_session(self, session_id: int) -> None:
        """Destroy a Janus session and clean up resources.

        Args:
            session_id: The unique identifier of the session to destroy.

        Note:
            This method should not be called directly from client code.
            Use the destroy() method on the JanusSession object instead.
        """
        if session_id in self.__sessions:
            del self.__sessions[session_id]
        else:
            logger.warning(f"Session ID not found: {session_id}")

        await self.dispatch_session_destroyed(session_id=session_id)

        # Also release transport resources if this is the last session
        if len(self.__sessions) == 0:
            await self.disconnect()

    @staticmethod
    def register_transport(
        protocol_matcher: Callable, transport_cls: "JanusTransport"
    ) -> None:
        """Register a transport implementation for automatic selection.

        Args:
            protocol_matcher: A callable that takes a base_url string and returns
                True if this transport can handle that URL protocol.
            transport_cls: The JanusTransport subclass to register for the
                matching protocol.
        """
        JanusTransport.__transport_implementation.append(
            (protocol_matcher, transport_cls)
        )

    @staticmethod
    def create_transport(
        base_url: str,
        api_secret: Optional[str] = None,
        token: Optional[str] = None,
        config: Dict = {},
    ) -> "JanusTransport":
        """Create an appropriate transport instance based on the URL protocol.

        Automatically selects and instantiates the correct transport implementation
        based on the base_url protocol. This method is typically called by
        JanusSession to create the transport automatically.

        Args:
            base_url: The base URL of the Janus server. The protocol determines
                which transport implementation is used.
            api_secret: Optional API secret for shared static secret authentication.
            token: Optional token for shared token-based authentication.
            config: Additional configuration parameters to pass to the transport
                constructor.

        Returns:
            An instance of the appropriate JanusTransport subclass for communicating
            with the Janus server.

        Raises:
            Exception: If no transport implementation matches the URL protocol.
            Exception: If multiple transport implementations match the URL protocol.
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

        raise Exception("No protocol matched")
