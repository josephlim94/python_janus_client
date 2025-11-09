"""Janus VideoRoom plugin implementation.

This module provides a client for the Janus VideoRoom plugin, which enables
multi-party video conferencing through WebRTC. The plugin supports:
- Room management (create, edit, destroy, list)
- Publisher functionality (join, publish, unpublish, configure)
- Subscriber functionality (subscribe, unsubscribe, switch feeds)
- Participant management (kick, moderate)
- RTP forwarding for external media processing
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from aiortc import MediaStreamTrack
from aiortc.contrib.media import MediaPlayer, MediaRecorder

from .plugin_base import JanusPlugin
from .message_transaction import is_subset

logger = logging.getLogger(__name__)


class VideoRoomError(Exception):
    """Exception raised for VideoRoom plugin errors."""

    def __init__(self, error_code: int, error_message: str):
        self.error_code = error_code
        self.error_message = error_message
        super().__init__(f"VideoRoom error {error_code}: {error_message}")


class VideoRoomEventType(Enum):
    """Types of events that can be received from the VideoRoom plugin."""

    JOINED = "joined"
    PUBLISHERS = "publishers"
    UNPUBLISHED = "unpublished"
    LEAVING = "leaving"
    DESTROYED = "destroyed"
    CONFIGURED = "configured"
    ATTACHED = "attached"
    UPDATED = "updated"
    STARTED = "started"
    SWITCHED = "switched"
    TALKING = "talking"
    STOPPED_TALKING = "stopped-talking"
    ERROR = "error"


class ParticipantType(Enum):
    """Types of participants in a VideoRoom."""

    PUBLISHER = "publisher"
    SUBSCRIBER = "subscriber"


class JanusVideoRoomPlugin(JanusPlugin):
    """Janus VideoRoom plugin client.

    This plugin provides multi-party video conferencing capabilities through WebRTC.
    It supports both publishing (sending media) and subscribing (receiving media) modes.

    Each plugin instance can be used as either a publisher or subscriber, but not both
    simultaneously. For applications that need both capabilities, create separate
    plugin instances.

    Example:
        ```python
        # Publisher example
        session = JanusSession(base_url="wss://example.com/janus")
        publisher = JanusVideoRoomPlugin()

        async with session:
            await publisher.attach(session)

            # Join as publisher
            await publisher.join_as_publisher(room=1234, display="Alice")

            # Register event handler
            def on_publishers(data):
                print(f"New publishers: {data['publishers']}")

            publisher.on_event(VideoRoomEventType.PUBLISHERS, on_publishers)

            # Publish media
            player = MediaPlayer("input.mp4")
            await publisher.publish(player)

            # Leave room
            await publisher.leave()
            await publisher.destroy()

        # Subscriber example
        subscriber = JanusVideoRoomPlugin()
        async with session:
            await subscriber.attach(session)

            # Subscribe to a publisher
            recorder = MediaRecorder("output.mp4")
            await subscriber.subscribe_to_publisher(
                room=1234,
                streams=[{"feed": 123}],
                recorder=recorder
            )

            await subscriber.destroy()
        ```
    """

    name = "janus.plugin.videoroom"

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the VideoRoom plugin.

        Args:
            **kwargs: Keyword arguments passed to JanusPlugin constructor.
                Supports pc_config parameter for WebRTC configuration.

        Examples:
            Basic usage:
            ```python
            plugin = JanusVideoRoomPlugin()
            ```

            With WebRTC configuration:
            ```python
            from aiortc import RTCConfiguration, RTCIceServer

            config = RTCConfiguration(iceServers=[
                RTCIceServer(urls='stun:stun.l.google.com:19302')
            ])
            plugin = JanusVideoRoomPlugin(pc_config=config)
            ```
        """
        super().__init__(**kwargs)
        self._participant_type: Optional[ParticipantType] = None
        self._room_id: Optional[int] = None
        self._publisher_id: Optional[int] = None
        self._private_id: Optional[int] = None
        self._display_name: Optional[str] = None
        self._is_publishing = False
        self._webrtcup_event = asyncio.Event()
        self._player: Optional[MediaPlayer] = None
        self._recorder: Optional[MediaRecorder] = None
        self._event_handlers: Dict[VideoRoomEventType, List[Callable]] = {
            event_type: [] for event_type in VideoRoomEventType
        }

    async def on_receive(self, response: Dict[str, Any]) -> None:
        """Handle incoming messages from Janus.

        Args:
            response: The response message from Janus.
        """
        if "jsep" in response:
            await self.on_receive_jsep(jsep=response["jsep"])

        janus_code = response["janus"]

        if janus_code == "webrtcup":
            logger.info("WebRTC connection established")
            self._webrtcup_event.set()

        elif janus_code == "hangup":
            logger.info("WebRTC connection closed")
            if self.pc.signalingState != "closed":
                await self.pc.close()

        elif janus_code == "media":
            if response.get("receiving") and self._recorder:
                # Start recording when media is received
                await self._recorder.start()

        elif janus_code == "event":
            await self._handle_event(response)

    async def _handle_event(self, response: Dict[str, Any]) -> None:
        """Handle VideoRoom events.

        Args:
            response: The event response from Janus.
        """
        if "plugindata" not in response:
            return

        plugin_data = response["plugindata"]["data"]
        videoroom_type = plugin_data["videoroom"]

        if videoroom_type == "joined":
            await self._trigger_event(VideoRoomEventType.JOINED, plugin_data)
        elif videoroom_type == "event":
            # Handle various event subtypes
            if "publishers" in plugin_data:
                await self._trigger_event(VideoRoomEventType.PUBLISHERS, plugin_data)
            elif "unpublished" in plugin_data:
                await self._trigger_event(VideoRoomEventType.UNPUBLISHED, plugin_data)
            elif "leaving" in plugin_data:
                await self._trigger_event(VideoRoomEventType.LEAVING, plugin_data)
            elif "configured" in plugin_data:
                await self._trigger_event(VideoRoomEventType.CONFIGURED, plugin_data)
            elif "started" in plugin_data:
                await self._trigger_event(VideoRoomEventType.STARTED, plugin_data)
            elif "switched" in plugin_data:
                await self._trigger_event(VideoRoomEventType.SWITCHED, plugin_data)
        elif videoroom_type == "attached":
            await self._trigger_event(VideoRoomEventType.ATTACHED, plugin_data)
        elif videoroom_type == "updated":
            await self._trigger_event(VideoRoomEventType.UPDATED, plugin_data)
        elif videoroom_type == "destroyed":
            await self._trigger_event(VideoRoomEventType.DESTROYED, plugin_data)
        elif videoroom_type in ["talking", "stopped-talking"]:
            event_type = (
                VideoRoomEventType.TALKING
                if videoroom_type == "talking"
                else VideoRoomEventType.STOPPED_TALKING
            )
            await self._trigger_event(event_type, plugin_data)

    def on_event(
        self, event_type: VideoRoomEventType, handler: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Register an event handler for VideoRoom events.

        Args:
            event_type: The type of event to handle.
            handler: Callback function to handle the event.
        """
        self._event_handlers[event_type].append(handler)

    async def _trigger_event(
        self, event_type: VideoRoomEventType, data: Dict[str, Any]
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

    def _check_error_in_response(self, response: Dict[str, Any]) -> None:
        """Check for errors in Janus response and raise VideoRoomError if found.

        Args:
            response: The response to check for errors.

        Raises:
            VideoRoomError: If an error is found in the response.
        """
        if is_subset(response, {"janus": "error", "error": {}}):
            error: Dict = response["error"]
            raise VideoRoomError(
                error.get("code", 0), error.get("reason", "Unknown error")
            )

        if is_subset(
            response,
            {
                "janus": "success",
                "plugindata": {"plugin": self.name, "data": {"error": None}},
            },
        ) or is_subset(
            response,
            {
                "janus": "event",
                "plugindata": {"plugin": self.name, "data": {"error": None}},
            },
        ):
            plugin_data = response["plugindata"]["data"]
            error_code: int = plugin_data.get("error_code", 0)
            error_message: str = plugin_data.get("error", "Unknown error")
            raise VideoRoomError(error_code, error_message)

    async def _send_request(
        self,
        body: Dict[str, Any],
        jsep: Optional[Dict[str, Any]] = None,
        timeout: float = 15.0,
    ) -> Dict[str, Any]:
        """Send a request to the VideoRoom plugin and wait for response.

        Args:
            body: The request body.
            jsep: Optional JSEP data to include.
            timeout: Maximum time to wait for response.

        Returns:
            The response data.

        Raises:
            VideoRoomError: If the request fails.
            TimeoutError: If the request times out.
        """

        def response_matcher(response: Dict[str, Any]) -> bool:
            return (
                is_subset(
                    response, {"janus": "success", "plugindata": {"plugin": self.name}}
                )
                or is_subset(
                    response, {"janus": "event", "plugindata": {"plugin": self.name}}
                )
                or is_subset(response, {"janus": "error", "error": {}})
            )

        message = {"janus": "message", "body": body}
        if jsep:
            message["jsep"] = jsep

        message_transaction = await self.send(message)
        response = await message_transaction.get(
            matcher=response_matcher, timeout=timeout
        )
        await message_transaction.done()

        if is_subset(response, {"janus": "event", "plugindata": {"plugin": self.name}}):
            await self._handle_event(response)

        self._check_error_in_response(response)
        return response

    def _setup_media_tracks(
        self, player: Optional[MediaPlayer], recorder: Optional[MediaRecorder]
    ) -> None:
        """Set up media tracks on the peer connection.

        Args:
            player: Media player for outgoing media.
            recorder: Media recorder for incoming media.
        """
        # Add outgoing tracks
        if player:
            if player.audio:
                self.pc.addTrack(player.audio)
            if player.video:
                self.pc.addTrack(player.video)

        # Set up incoming track handler
        if recorder:

            @self.pc.on("track")
            async def on_track(track: MediaStreamTrack):
                logger.info(f"VideoRoom: Received {track.kind} track")
                recorder.addTrack(track)

        self._player = player
        self._recorder = recorder

    async def create_room(
        self,
        room_id: Optional[int] = None,
        description: Optional[str] = None,
        secret: Optional[str] = None,
        pin: Optional[str] = None,
        is_private: bool = False,
        publishers: int = 3,
        bitrate: Optional[int] = None,
        fir_freq: int = 0,
        audiocodec: Optional[str] = None,
        videocodec: Optional[str] = None,
        record: bool = False,
        rec_dir: Optional[str] = None,
        permanent: bool = False,
        admin_key: Optional[str] = None,
        timeout: float = 15.0,
        **kwargs: Any,
    ) -> int:
        """Create a new VideoRoom.

        Args:
            room_id: Unique room ID (auto-generated if not provided).
            description: Room description.
            secret: Secret for room management.
            pin: PIN required to join the room.
            is_private: Whether the room should be private.
            publishers: Maximum number of concurrent publishers.
            bitrate: Maximum video bitrate for publishers.
            fir_freq: FIR frequency for keyframe requests.
            audiocodec: Allowed audio codecs (comma-separated).
            videocodec: Allowed video codecs (comma-separated).
            record: Whether to record the room.
            rec_dir: Directory for recordings.
            permanent: Whether to save room to config file.
            admin_key: Admin key if required by server.
            timeout: Maximum time to wait for response.
            **kwargs: Additional room configuration parameters.

        Returns:
            The created room ID.

        Raises:
            VideoRoomError: If creation fails.
            TimeoutError: If request times out.
        """
        body: Dict[str, Any] = {
            "request": "create",
            "is_private": is_private,
            "publishers": publishers,
            "fir_freq": fir_freq,
            "record": record,
            "permanent": permanent,
        }

        if room_id is not None:
            body["room"] = room_id
        if description:
            body["description"] = description
        if secret:
            body["secret"] = secret
        if pin:
            body["pin"] = pin
        if bitrate:
            body["bitrate"] = bitrate
        if audiocodec:
            body["audiocodec"] = audiocodec
        if videocodec:
            body["videocodec"] = videocodec
        if rec_dir:
            body["rec_dir"] = rec_dir
        if admin_key:
            body["admin_key"] = admin_key

        # Add any additional configuration
        body.update(kwargs)

        response = await self._send_request(body, timeout=timeout)
        return int(response["plugindata"]["data"]["room"])

    async def destroy_room(
        self,
        room_id: int,
        secret: Optional[str] = None,
        permanent: bool = False,
        timeout: float = 15.0,
    ) -> None:
        """Destroy a VideoRoom.

        Args:
            room_id: The room ID to destroy.
            secret: Room secret if required.
            permanent: Whether to remove from config file.
            timeout: Maximum time to wait for response.

        Raises:
            VideoRoomError: If destruction fails.
            TimeoutError: If request times out.
        """
        body: Dict[str, Any] = {
            "request": "destroy",
            "room": room_id,
            "permanent": permanent,
        }

        if secret:
            body["secret"] = secret

        await self._send_request(body, timeout=timeout)

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
            VideoRoomError: If request fails.
            TimeoutError: If request times out.
        """
        body: Dict[str, Any] = {"request": "list"}
        if admin_key:
            body["admin_key"] = admin_key

        response = await self._send_request(body, timeout=timeout)
        return response["plugindata"]["data"].get("list", [])

    async def list_participants(
        self, room_id: int, timeout: float = 15.0
    ) -> List[Dict[str, Any]]:
        """List participants in a room.

        Args:
            room_id: The room ID to query.
            timeout: Maximum time to wait for response.

        Returns:
            List of participant information dictionaries.

        Raises:
            VideoRoomError: If request fails.
            TimeoutError: If request times out.
        """
        body = {"request": "listparticipants", "room": room_id}
        response = await self._send_request(body, timeout=timeout)
        return response["plugindata"]["data"].get("participants", [])

    async def exists(self, room_id: int, timeout: float = 15.0) -> bool:
        """Check if a room exists.

        Args:
            room_id: The room ID to check.
            timeout: Maximum time to wait for response.

        Returns:
            True if the room exists, False otherwise.

        Raises:
            VideoRoomError: If request fails.
            TimeoutError: If request times out.
        """
        body = {"request": "exists", "room": room_id}
        response = await self._send_request(body, timeout=timeout)
        return response["plugindata"]["data"].get("exists", False)

    async def join_as_publisher(
        self,
        room_id: int,
        publisher_id: Optional[int] = None,
        display: Optional[str] = None,
        token: Optional[str] = None,
        timeout: float = 15.0,
    ) -> Dict[str, Any]:
        """Join a room as a publisher. Emits VideoRoomEventType.JOINED event.

        Args:
            room_id: The room ID to join.
            publisher_id: Unique publisher ID (auto-generated if not provided).
            display: Display name for the publisher.
            token: Invitation token if room has ACL.
            timeout: Maximum time to wait for response.

        Returns:
            Join response containing room info and current publishers.

        Raises:
            VideoRoomError: If join fails.
            TimeoutError: If request times out.
        """
        body: Dict[str, Any] = {
            "request": "join",
            "ptype": "publisher",
            "room": room_id,
        }

        if publisher_id is not None:
            body["id"] = publisher_id
        if display:
            body["display"] = display
        if token:
            body["token"] = token

        response = await self._send_request(body, timeout=timeout)

        # Store state
        self._participant_type = ParticipantType.PUBLISHER
        self._room_id = room_id
        plugin_data = response["plugindata"]["data"]
        self._publisher_id = plugin_data["id"]
        self._private_id = plugin_data["private_id"]
        self._display_name = display

        return plugin_data

    async def publish(
        self,
        player: MediaPlayer,
        audiocodec: Optional[str] = None,
        videocodec: Optional[str] = None,
        bitrate: Optional[int] = None,
        record: bool = False,
        filename: Optional[str] = None,
        descriptions: Optional[List[Dict[str, str]]] = None,
        trickle: bool = False,
        timeout: float = 30.0,
    ) -> dict:
        """Publish media streams to the room.

        Args:
            player: MediaPlayer for outgoing media streams.
            audiocodec: Preferred audio codec.
            videocodec: Preferred video codec.
            bitrate: Bitrate cap for REMB.
            record: Whether to record this publisher.
            filename: Base filename for recordings.
            descriptions: Stream descriptions for UI rendering.
            trickle: Whether to use trickle ICE.
            timeout: Maximum time to wait for response.

        Raises:
            VideoRoomError: If publish fails.
            TimeoutError: If request times out.
        """
        if self._participant_type != ParticipantType.PUBLISHER:
            raise VideoRoomError(-1, "Must join as publisher before publishing")

        # Set up media tracks
        self._setup_media_tracks(player, None)

        # Create offer
        await self.pc.setLocalDescription(await self.pc.createOffer())

        body: Dict[str, Any] = {"request": "publish", "record": record}

        if audiocodec:
            body["audiocodec"] = audiocodec
        if videocodec:
            body["videocodec"] = videocodec
        if bitrate:
            body["bitrate"] = bitrate
        if filename:
            body["filename"] = filename
        if descriptions:
            body["descriptions"] = descriptions

        jsep = await self.create_jsep(self.pc, trickle=trickle)
        response = await self._send_request(body, jsep=jsep, timeout=timeout)

        # Handle JSEP answer
        if "jsep" in response:
            await self.on_receive_jsep(response["jsep"])

        self._is_publishing = True

        return response["plugindata"]["data"]

    async def unpublish(self, timeout: float = 15.0) -> None:
        """Stop publishing media.

        Args:
            timeout: Maximum time to wait for response.

        Raises:
            VideoRoomError: If unpublish fails.
            TimeoutError: If request times out.
        """
        body = {"request": "unpublish"}
        await self._send_request(body, timeout=timeout)
        self._is_publishing = False

    async def configure(
        self,
        bitrate: Optional[int] = None,
        keyframe: bool = False,
        record: Optional[bool] = None,
        filename: Optional[str] = None,
        display: Optional[str] = None,
        streams: Optional[List[Dict[str, Any]]] = None,
        descriptions: Optional[List[Dict[str, str]]] = None,
        timeout: float = 15.0,
    ) -> None:
        """Configure publisher settings.

        Args:
            bitrate: New bitrate cap.
            keyframe: Whether to request a keyframe.
            record: Whether to record this publisher.
            filename: Base filename for recordings.
            display: New display name.
            streams: Stream-specific configurations.
            descriptions: Updated stream descriptions.
            timeout: Maximum time to wait for response.

        Raises:
            VideoRoomError: If configure fails.
            TimeoutError: If request times out.
        """
        body: Dict[str, Any] = {"request": "configure"}

        if bitrate is not None:
            body["bitrate"] = bitrate
        if keyframe:
            body["keyframe"] = keyframe
        if record is not None:
            body["record"] = record
        if filename:
            body["filename"] = filename
        if display:
            body["display"] = display
            self._display_name = display
        if streams:
            body["streams"] = streams
        if descriptions:
            body["descriptions"] = descriptions

        await self._send_request(body, timeout=timeout)

    async def subscribe_to_publisher(
        self,
        room_id: int,
        streams: List[Dict[str, Any]],
        recorder: Optional[MediaRecorder] = None,
        private_id: Optional[int] = None,
        use_msid: bool = False,
        autoupdate: bool = True,
        trickle: bool = False,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Subscribe to publisher streams.

        Args:
            room_id: The room ID containing the publishers.
            streams: List of stream configurations to subscribe to.
                Each stream should have at least a 'feed' key with publisher ID.
            recorder: MediaRecorder for incoming media streams.
            private_id: Private ID for association with publisher.
            use_msid: Whether to include msid referencing the publisher.
            autoupdate: Whether to auto-update on publisher changes.
            trickle: Whether to use trickle ICE.
            timeout: Maximum time to wait for response.

        Returns:
            Subscription information.

        Raises:
            VideoRoomError: If subscription fails.
            TimeoutError: If request times out.
        """
        if self._participant_type == ParticipantType.PUBLISHER:
            raise VideoRoomError(
                -1,
                f"Can only be either publisher or subscriber. Now {self._participant_type}",
            )

        body: Dict[str, Any] = {
            "request": "join",
            "ptype": "subscriber",
            "room": room_id,
            "streams": streams,
            "use_msid": use_msid,
            "autoupdate": autoupdate,
        }

        if private_id is not None:
            body["private_id"] = private_id

        response = await self._send_request(body, timeout=timeout)

        # Store state
        self._participant_type = ParticipantType.SUBSCRIBER
        self._room_id = room_id

        # Set up media tracks for recording
        self._setup_media_tracks(None, recorder)

        # Handle JSEP offer
        if "jsep" in response:
            await self.on_receive_jsep(response["jsep"])
            await self.pc.setLocalDescription(await self.pc.createAnswer())

            # Send answer
            await self.start(trickle=trickle, timeout=timeout)

        return response["plugindata"]["data"]

    async def start(self, trickle: bool = False, timeout: float = 15.0) -> None:
        """Start receiving media (send JSEP answer).

        Args:
            trickle: Whether to use trickle ICE.
            timeout: Maximum time to wait for response.

        Raises:
            VideoRoomError: If start fails.
            TimeoutError: If request times out.
        """
        body = {"request": "start"}
        jsep = await self.create_jsep(self.pc, trickle=trickle)
        await self._send_request(body, jsep=jsep, timeout=timeout)

    async def pause(self, timeout: float = 15.0) -> None:
        """Pause media delivery.

        Args:
            timeout: Maximum time to wait for response.

        Raises:
            VideoRoomError: If pause fails.
            TimeoutError: If request times out.
        """
        body = {"request": "pause"}
        await self._send_request(body, timeout=timeout)

    async def subscribe(
        self, streams: List[Dict[str, Any]], timeout: float = 15.0
    ) -> None:
        """Subscribe to additional streams.

        Args:
            streams: List of new streams to subscribe to.
            timeout: Maximum time to wait for response.

        Raises:
            VideoRoomError: If subscription fails.
            TimeoutError: If request times out.
        """
        body = {"request": "subscribe", "streams": streams}
        response = await self._send_request(body, timeout=timeout)

        # Handle potential renegotiation
        if "jsep" in response:
            await self.on_receive_jsep(response["jsep"])
            await self.pc.setLocalDescription(await self.pc.createAnswer())
            await self.start(timeout=timeout)

    async def unsubscribe(
        self, streams: List[Dict[str, Any]], timeout: float = 15.0
    ) -> None:
        """Unsubscribe from streams.

        Args:
            streams: List of streams to unsubscribe from.
            timeout: Maximum time to wait for response.

        Raises:
            VideoRoomError: If unsubscription fails.
            TimeoutError: If request times out.
        """
        body = {"request": "unsubscribe", "streams": streams}
        response = await self._send_request(body, timeout=timeout)

        # Handle potential renegotiation
        if "jsep" in response:
            await self.on_receive_jsep(response["jsep"])
            await self.pc.setLocalDescription(await self.pc.createAnswer())
            await self.start(timeout=timeout)

    async def switch_publisher(
        self, streams: List[Dict[str, Any]], timeout: float = 15.0
    ) -> None:
        """Switch to different publisher streams without renegotiation.

        Args:
            streams: List of stream switches to perform.
                Each should have 'feed', 'mid', and 'sub_mid' keys.
            timeout: Maximum time to wait for response.

        Raises:
            VideoRoomError: If switch fails.
            TimeoutError: If request times out.
        """
        body = {"request": "switch", "streams": streams}
        await self._send_request(body, timeout=timeout)

    # Common Methods

    async def leave(self, timeout: float = 15.0) -> None:
        """Leave the room.

        Args:
            timeout: Maximum time to wait for response.

        Raises:
            VideoRoomError: If leave fails.
            TimeoutError: If request times out.
        """
        body = {"request": "leave"}
        await self._send_request(body, timeout=timeout)

        # Reset state
        self._participant_type = None
        self._room_id = None
        self._publisher_id = None
        self._private_id = None
        self._display_name = None
        self._is_publishing = False

    # Administrative Methods

    async def kick_participant(
        self, room_id: int, participant_id: int, secret: str, timeout: float = 15.0
    ) -> None:
        """Kick a participant from the room.

        Args:
            room_id: The room ID.
            participant_id: ID of participant to kick.
            secret: Room secret for authorization.
            timeout: Maximum time to wait for response.

        Raises:
            VideoRoomError: If kick fails.
            TimeoutError: If request times out.
        """
        body = {
            "request": "kick",
            "room": room_id,
            "id": participant_id,
            "secret": secret,
        }
        await self._send_request(body, timeout=timeout)

    async def moderate_participant(
        self,
        room_id: int,
        participant_id: int,
        mid: str,
        mute: bool,
        secret: str,
        timeout: float = 15.0,
    ) -> None:
        """Moderate a participant's media stream.

        Args:
            room_id: The room ID.
            participant_id: ID of participant to moderate.
            mid: Media line ID to moderate.
            mute: Whether to mute (True) or unmute (False).
            secret: Room secret for authorization.
            timeout: Maximum time to wait for response.

        Raises:
            VideoRoomError: If moderation fails.
            TimeoutError: If request times out.
        """
        body = {
            "request": "moderate",
            "room": room_id,
            "id": participant_id,
            "mid": mid,
            "mute": mute,
            "secret": secret,
        }
        await self._send_request(body, timeout=timeout)

    async def _cleanup_media(self) -> None:
        """Clean up media resources."""
        if self._recorder:
            try:
                await self._recorder.stop()
            except Exception as e:
                logger.warning(f"Error stopping recorder: {e}")
            self._recorder = None

        if self._player:
            # MediaPlayer doesn't have an async stop method
            self._player = None

        # Reset peer connection if needed
        if self.pc.signalingState != "closed":
            await self.reset_connection()

    async def destroy(self) -> None:
        """Destroy the plugin and clean up all resources."""
        # Clean up media first
        await self._cleanup_media()

        # Clear state
        self._participant_type = None
        self._room_id = None
        self._publisher_id = None
        self._private_id = None
        self._display_name = None
        self._is_publishing = False
        self._webrtcup_event.clear()

        # Call parent destroy
        await super().destroy()

    @property
    def room_id(self) -> Optional[int]:
        """Get the current room ID."""
        return self._room_id

    @property
    def publisher_id(self) -> Optional[int]:
        """Get the current publisher ID."""
        return self._publisher_id

    @property
    def private_id(self) -> Optional[int]:
        """Get the current private ID."""
        return self._private_id

    @property
    def display_name(self) -> Optional[str]:
        """Get the current display name."""
        return self._display_name

    @property
    def participant_type(self) -> Optional[ParticipantType]:
        """Get the current participant type."""
        return self._participant_type

    @property
    def is_publishing(self) -> bool:
        """Check if currently publishing media."""
        return self._is_publishing

    @property
    def webrtcup_event(self) -> asyncio.Event:
        """Return webrtc up event"""
        return self._webrtcup_event
