"""Janus TextRoom plugin implementation.

This module provides a client for the Janus TextRoom plugin, which enables
DataChannel-based text communication in rooms. The plugin supports:
- Room management (create, edit, destroy, list)
- Participant management (join, leave, kick)
- Messaging (public broadcasts and private whispers)
- Room announcements
- Message history
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.rtcdatachannel import RTCDataChannel

from .plugin_base import JanusPlugin
from .message_transaction import is_subset

logger = logging.getLogger(__name__)


class TextRoomError(Exception):
    """Exception raised for TextRoom plugin errors."""

    def __init__(self, error_code: int, error_message: str):
        self.error_code = error_code
        self.error_message = error_message
        super().__init__(f"TextRoom error {error_code}: {error_message}")


class TextRoomEventType(Enum):
    """Types of events that can be received from the TextRoom plugin."""

    JOIN = "join"
    LEAVE = "leave"
    KICKED = "kicked"
    DESTROYED = "destroyed"
    MESSAGE = "message"
    ANNOUNCEMENT = "announcement"
    ERROR = "error"


class JanusTextRoomPlugin(JanusPlugin):
    """Janus TextRoom plugin client.

    This plugin provides text-based communication through WebRTC DataChannels.
    It supports multiple rooms, public and private messaging, and room management.
    From my observation, the datachannel is only created after a room is joined, so
    the first join request cannot be sent through datachannel.

    Example:
        ```python
        session = JanusSession(base_url="wss://example.com/janus")
        plugin = JanusTextRoomPlugin()

        async with session:
            await plugin.attach(session)
            await plugin.setup()

            # Join a room
            participants = await plugin.join_room(room=1234, username="alice")

            # Register message handler
            def on_message(data):
                print(f"Message from {data['from']}: {data['text']}")

            plugin.on_event(TextRoomEventType.MESSAGE, on_message)

            # Send a message
            await plugin.send_message(room=1234, text="Hello, world!")

            # Leave the room
            await plugin.leave_room(room=1234)

            await plugin.destroy()
        ```
    """

    name = "janus.plugin.textroom"

    def __init__(self) -> None:
        super().__init__()
        self._data_channel: Optional[RTCDataChannel] = None
        self._webrtcup_event = asyncio.Event()
        self._data_channel_created_event = asyncio.Event()
        self._event_handlers: Dict[TextRoomEventType, List[Callable]] = {
            event_type: [] for event_type in TextRoomEventType
        }
        self._pending_transactions: Dict[str, asyncio.Event] = {}
        self._transaction_responses: Dict[str, Dict[str, Any]] = {}

    async def on_receive(self, response: Dict[str, Any]) -> None:
        """Handle incoming messages from Janus.

        Args:
            response: The response message from Janus.
        """
        if "jsep" in response:
            await self.on_receive_jsep(jsep=response["jsep"])

        janus_code = response.get("janus")

        if janus_code == "webrtcup":
            logger.info("WebRTC connection established")
            self._webrtcup_event.set()

        elif janus_code == "hangup":
            logger.info("WebRTC connection closed")
            if self._pc:
                await self._pc.close()

        # elif janus_code == "event":
        #     logger.info("Received setup complete event")
        #     plugin_data = response["plugindata"].get("data", {})
        #     textroom_type = plugin_data.get("textroom")

        # if textroom_type == "event":
        #     result = plugin_data.get("result")
        #     if result == "ok":
        #         self._setup_complete.set()

    def on_event(
        self, event_type: TextRoomEventType, handler: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Register an event handler for TextRoom events.

        Args:
            event_type: The type of event to handle.
            handler: Callback function to handle the event.
        """
        self._event_handlers[event_type].append(handler)

    async def _trigger_event(
        self, event_type: TextRoomEventType, data: Dict[str, Any]
    ) -> None:
        """Trigger registered event handlers.

        Args:
            event_type: The type of event that occurred.
            data: Event data to pass to handlers.
        """
        for handler in self._event_handlers[event_type]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")

    def _setup_datachannel_handlers(self, channel: RTCDataChannel) -> None:
        """Set up handlers for datachannel events.

        Args:
            channel: The datachannel to set up handlers for.
        """

        @channel.on("open")
        def on_open():
            logger.info("DataChannel opened")

        @channel.on("close")
        def on_close():
            logger.info("DataChannel closed")

        @channel.on("message")
        async def on_message(message: str):
            logger.info(f"DataChannel message: {message}")
            await self._handle_datachannel_message(message)

    async def _handle_datachannel_message(self, message: str) -> None:
        """Handle incoming datachannel messages.

        Args:
            message: The message received on the datachannel.
        """
        data: dict = json.loads(message)
        textroom_type = data["textroom"]
        transaction = data.get("transaction")

        # Check if this is a response to a pending transaction
        if transaction and transaction in self._pending_transactions:
            self._transaction_responses[transaction] = data
            self._pending_transactions[transaction].set()
            return

        # Otherwise, trigger event handlers
        if textroom_type == "join":
            await self._trigger_event(TextRoomEventType.JOIN, data)
        elif textroom_type == "leave":
            await self._trigger_event(TextRoomEventType.LEAVE, data)
        elif textroom_type == "kicked":
            await self._trigger_event(TextRoomEventType.KICKED, data)
        elif textroom_type == "destroyed":
            await self._trigger_event(TextRoomEventType.DESTROYED, data)
        elif textroom_type == "message":
            await self._trigger_event(TextRoomEventType.MESSAGE, data)
        elif textroom_type == "announcement":
            await self._trigger_event(TextRoomEventType.ANNOUNCEMENT, data)
        elif textroom_type == "error":
            await self._trigger_event(TextRoomEventType.ERROR, data)
        elif textroom_type == "success":
            # Generic success response
            pass

    async def _send_datachannel_request(
        self, body: Dict[str, Any], timeout: float = 15.0
    ) -> Dict[str, Any]:
        """Send a request via datachannel and wait for response.

        Args:
            body: The request body to send.
            timeout: Maximum time to wait for response.

        Returns:
            The response data.

        Raises:
            TextRoomError: If the request fails.
            TimeoutError: If the request times out.
        """
        if not self._data_channel:
            raise TextRoomError(0, "DataChannel not established")

        transaction = uuid.uuid4().hex
        body["transaction"] = transaction

        # Register pending transaction
        self._pending_transactions[transaction] = asyncio.Event()

        try:
            # Send the request
            self._data_channel.send(json.dumps(body))

            # Wait for response
            await asyncio.wait_for(
                self._pending_transactions[transaction].wait(), timeout=timeout
            )

            # Get response
            response = self._transaction_responses.pop(transaction)

            # Check for errors
            if response.get("textroom") == "error":
                raise TextRoomError(
                    response.get("error_code", 0), response.get("error", "")
                )

            return response

        finally:
            # Clean up
            self._pending_transactions.pop(transaction, None)
            self._transaction_responses.pop(transaction, None)

    def check_error_in_response(self, response: dict) -> None:
        if is_subset(response, {"janus": "error", "error": {}}):
            error: Dict = response["error"]
            raise TextRoomError(
                error.get("code", 0), error.get("reason", "Unknown error")
            )

        if is_subset(
            response,
            {
                "janus": "success",
                "plugindata": {"plugin": self.name, "data": {"error": None}},
            },
        ):
            error_code: int = response["plugindata"]["data"]["error_code"]
            error_message: str = response["plugindata"]["data"]["error"]
            raise TextRoomError(error_code, error_message)

    async def send_wrapper(self, message: dict, matcher: dict, timeout: float) -> dict:
        def function_matcher(response: dict):
            return (
                is_subset(
                    response,
                    {
                        "janus": "success",
                        "plugindata": {
                            "plugin": self.name,
                            "data": matcher,
                        },
                    },
                )
                or is_subset(
                    response,
                    {
                        "janus": "success",
                        "plugindata": {
                            "plugin": self.name,
                            "data": {
                                "textroom": "event",
                            },
                        },
                    },
                )
                or is_subset(response, {"janus": "error", "error": {}})
            )

        message_transaction = await self.send(
            message={
                "janus": "message",
                "body": message,
            },
        )
        message_response = await message_transaction.get(
            matcher=function_matcher, timeout=timeout
        )
        await message_transaction.done()

        self.check_error_in_response(response=message_response)

        return message_response

    async def setup(self, timeout: float = 30.0) -> None:
        """Initialize the WebRTC connection for the TextRoom plugin.

        This must be called before joining rooms or sending messages.

        Args:
            timeout: Maximum time to wait for setup completion.

        Raises:
            TimeoutError: If setup doesn't complete within timeout.
            TextRoomError: If setup fails.
        """

        def response_matcher_base(response: dict):
            return is_subset(response, {"janus": "error", "error": {}}) or is_subset(
                response, {"janus": "success", "plugindata": {"plugin": self.name}}
            )

        message_transaction = await self.send(
            message={
                "janus": "message",
                "body": {"request": "setup"},
            },
        )
        response = await message_transaction.get(
            matcher=lambda r: is_subset(r, {"janus": "ack"})
            or is_subset(
                r,
                {
                    "janus": "event",
                    "plugindata": {
                        "plugin": self.name,
                        "data": {
                            "textroom": "event",
                            "result": "ok",
                        },
                    },
                },
            )
            or response_matcher_base(r),
            timeout=timeout,
        )
        self.check_error_in_response(response=response)

        # If it got "ack" first, the second message is the "event" with jsep
        logger.info(response)
        if is_subset(response, {"janus": "ack"}):
            logger.info("Get another response")
            response = await message_transaction.get(
                matcher=lambda r: is_subset(
                    r,
                    {
                        "janus": "event",
                        "plugindata": {
                            "plugin": self.name,
                            "data": {
                                "textroom": "event",
                                "result": "ok",
                            },
                        },
                    },
                )
                or response_matcher_base(r),
                timeout=timeout,
            )
            self.check_error_in_response(response=response)

        await message_transaction.done()
        logger.info(response)

        if "jsep" not in response:
            raise TextRoomError(0, "No JSEP offer received from setup")

        # Create new peer connection for this setup
        self._pc = RTCPeerConnection()

        # Set up peer connection handlers
        @self._pc.on("datachannel")
        def on_datachannel(channel: RTCDataChannel):
            logger.info(f"DataChannel '{channel.label}' created by remote party")
            self._data_channel = channel
            self._data_channel_created_event.set()
            self._setup_datachannel_handlers(channel)

        await self._pc.setRemoteDescription(
            RTCSessionDescription(
                sdp=response["jsep"]["sdp"], type=response["jsep"]["type"]
            )
        )

        await self._pc.setLocalDescription(await self._pc.createAnswer())

        # Send answer
        ack_transaction = await self.send(
            {
                "janus": "message",
                "body": {"request": "ack"},
                "jsep": await self.create_jsep(self._pc),
            }
        )
        await ack_transaction.get(
            matcher={
                "janus": "event",
                "plugindata": {
                    "plugin": self.name,
                    "data": {
                        "textroom": "event",
                        "result": "ok",
                    },
                },
            },
            timeout=timeout,
        )
        await ack_transaction.done()

        # # Wait for setup to complete
        # await asyncio.wait_for(self._setup_complete.wait(), timeout=timeout)

        # Wait for webrtc to be connected
        await asyncio.wait_for(self._webrtcup_event.wait(), timeout=timeout)

    async def list_rooms(
        self, admin_key: Optional[str] = None, timeout: float = 15.0
    ) -> List[Dict[str, Any]]:
        """List available rooms.

        Args:
            admin_key: Optional admin key for accessing private rooms.
            timeout: Maximum time to wait for response.

        Returns:
            List of room information dictionaries.

        Raises:
            TimeoutError: If request times out.
            TextRoomError: If request fails.
        """
        body = {"request": "list"}
        if admin_key:
            body["admin_key"] = admin_key

        response = await self.send_wrapper(
            message=body, matcher={"textroom": "success"}, timeout=timeout
        )

        return response["plugindata"]["data"].get("list", [])

    async def list_participants(
        self, room: int, timeout: float = 15.0
    ) -> List[Dict[str, Any]]:
        """List participants in a room.

        Args:
            room: The room ID to query.
            timeout: Maximum time to wait for response.

        Returns:
            List of participant information dictionaries.

        Raises:
            TimeoutError: If request times out.
            TextRoomError: If request fails.
        """
        response = await self.send_wrapper(
            message={"request": "listparticipants", "room": room},
            matcher={"room": room},
            timeout=timeout,
        )

        return response["plugindata"]["data"].get("participants", [])

    async def create_room(
        self,
        room: Optional[int] = None,
        description: Optional[str] = None,
        secret: Optional[str] = None,
        pin: Optional[str] = None,
        is_private: bool = True,
        history: int = 0,
        post: Optional[str] = None,
        admin_key: Optional[str] = None,
        permanent: bool = False,
        timeout: float = 15.0,
    ) -> int:
        """Create a new TextRoom.

        Args:
            room: Room ID to assign (optional, auto-generated if not provided).
            description: Room description.
            secret: Secret for room management.
            pin: PIN required to join the room.
            is_private: Whether the room should be private.
            history: Number of messages to store as history.
            post: HTTP backend URL for message forwarding.
            admin_key: Admin key if required by server.
            permanent: Whether to save room to config file.
            timeout: Maximum time to wait for response.

        Returns:
            The created room ID.

        Raises:
            TimeoutError: If request times out.
            TextRoomError: If creation fails.
        """
        body: Dict[str, Any] = {"request": "create", "is_private": is_private}

        if room is not None:
            body["room"] = room
        if description:
            body["description"] = description
        if secret:
            body["secret"] = secret
        if pin:
            body["pin"] = pin
        if history > 0:
            body["history"] = history
        if post:
            body["post"] = post
        if admin_key:
            body["admin_key"] = admin_key
        if permanent:
            body["permanent"] = permanent

        response = await self.send_wrapper(
            message=body,
            matcher={"textroom": "created"},
            timeout=timeout,
        )

        return response["plugindata"]["data"]["room"]

    async def destroy_room(
        self,
        room: int,
        secret: Optional[str] = None,
        permanent: bool = False,
        timeout: float = 15.0,
    ) -> None:
        """Destroy a TextRoom.

        Args:
            room: The room ID to destroy.
            secret: Room secret if required.
            permanent: Whether to remove from config file.
            timeout: Maximum time to wait for response.

        Raises:
            TimeoutError: If request times out.
            TextRoomError: If destruction fails.
        """
        body: Dict[str, Any] = {"request": "destroy", "room": room}

        if secret:
            body["secret"] = secret
        if permanent:
            body["permanent"] = permanent

        await self.send_wrapper(
            message=body,
            matcher={"textroom": "destroyed"},
            timeout=timeout,
        )

    async def join_room(
        self,
        room: int,
        username: str,
        display: Optional[str] = None,
        pin: Optional[str] = None,
        token: Optional[str] = None,
        history: bool = True,
        timeout: float = 15.0,
    ) -> List[Dict[str, Any]]:
        """Join a TextRoom.

        Args:
            room: The room ID to join.
            username: Unique username for this participant.
            display: Display name for this participant.
            pin: Room PIN if required.
            token: Invitation token if room has ACL.
            history: Whether to retrieve message history.
            timeout: Maximum time to wait for response.

        Returns:
            List of current participants in the room.

        Raises:
            TimeoutError: If request times out.
            TextRoomError: If join fails.
        """

        body: Dict[str, Any] = {
            "request": "list",  # Bug in Janus, must have "request" field when not sent over datachannel
            "textroom": "join",
            "room": room,
            "username": username,
            "history": history,
        }

        if display:
            body["display"] = display
        if pin:
            body["pin"] = pin
        if token:
            body["token"] = token

        response = await self.send_wrapper(
            message=body,
            matcher={"textroom": "success"},
            timeout=timeout,
        )

        # I believe datachannel is always created after join room
        # Wait for it
        await asyncio.wait_for(self._data_channel_created_event.wait(), timeout=timeout)

        return response["plugindata"]["data"]["participants"]

    async def leave_room(self, room: int, timeout: float = 15.0) -> None:
        """Leave a TextRoom.

        Args:
            room: The room ID to leave.
            timeout: Maximum time to wait for response.

        Raises:
            TimeoutError: If request times out.
            TextRoomError: If leave fails.
        """
        body = {"textroom": "leave", "room": room}
        await self._send_datachannel_request(body, timeout)

    async def send_message(
        self,
        room: int,
        text: str,
        to: Optional[str] = None,
        tos: Optional[List[str]] = None,
        ack: bool = True,
        timeout: float = 15.0,
    ) -> None:
        """Send a message in a TextRoom.

        Args:
            room: The room ID to send the message to.
            text: The message text to send.
            to: Username to send private message to (optional).
            tos: List of usernames to send private message to (optional).
            ack: Whether to wait for acknowledgment.
            timeout: Maximum time to wait for acknowledgment.

        Raises:
            TimeoutError: If request times out.
            TextRoomError: If send fails.
        """
        if not self._data_channel:
            raise TextRoomError(0, "DataChannel not established")

        body: Dict[str, Any] = {
            "textroom": "message",
            "room": room,
            "text": text,
            "ack": ack,
        }

        if to:
            body["to"] = to
        if tos:
            body["tos"] = tos

        if ack:
            await self._send_datachannel_request(body, timeout)
        else:
            # Send without waiting for response
            transaction = uuid.uuid4().hex
            body["transaction"] = transaction
            self._data_channel.send(json.dumps(body))

    async def send_announcement(
        self,
        room: int,
        text: str,
        secret: str,
        timeout: float = 15.0,
    ) -> None:
        """Send an announcement to a TextRoom.

        Args:
            room: The room ID to send the announcement to.
            text: The announcement text.
            secret: Room secret for authorization.
            timeout: Maximum time to wait for response.

        Raises:
            TimeoutError: If request times out.
            TextRoomError: If send fails.
        """
        body = {
            "textroom": "announcement",
            "room": room,
            "text": text,
            "secret": secret,
        }
        await self._send_datachannel_request(body, timeout)

    async def kick_participant(
        self, room: int, username: str, secret: str, timeout: float = 15.0
    ) -> None:
        """Kick a participant from a TextRoom.

        Args:
            room: The room ID.
            username: Username of participant to kick.
            secret: Room secret for authorization.
            timeout: Maximum time to wait for response.

        Raises:
            TimeoutError: If request times out.
            TextRoomError: If kick fails.
        """
        body = {
            "textroom": "kick",
            "room": room,
            "username": username,
            "secret": secret,
        }
        await self._send_datachannel_request(body, timeout)
