"""Janus VideoCall plugin implementation.

This module provides a client for the Janus VideoCall plugin, which enables
peer-to-peer video calling through the Janus gateway. The plugin supports:
- User registration with unique usernames
- Initiating and receiving video calls
- Media control (audio/video mute, bitrate limits)
- Call recording capabilities
- Proper WebRTC signaling and media handling
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable, Awaitable
from enum import Enum

from aiortc.contrib.media import MediaPlayer, MediaRecorder
from aiortc import MediaStreamTrack, RTCSessionDescription

from .plugin_base import JanusPlugin
from .message_transaction import is_subset

logger = logging.getLogger(__name__)


class VideoCallError(Exception):
    """Exception raised for VideoCall plugin errors."""

    def __init__(self, error_code: int, error_message: str):
        self.error_code = error_code
        self.error_message = error_message
        super().__init__(f"VideoCall error {error_code}: {error_message}")


class VideoCallEventType(Enum):
    """Types of events that can be received from the VideoCall plugin."""

    REGISTERED = "registered"
    CALLING = "calling"
    INCOMINGCALL = "incomingcall"
    ACCEPTED = "accepted"
    UPDATE = "update"
    HANGUP = "hangup"
    SET = "set"


class JanusVideoCallPlugin(JanusPlugin):
    """Janus VideoCall plugin client.

    This plugin provides peer-to-peer video calling capabilities through the
    Janus gateway. It supports user registration, call initiation/acceptance,
    media control, and proper WebRTC signaling.

    Example:
        ```python
        session = JanusSession(base_url="wss://example.com/janus")
        plugin = JanusVideoCallPlugin()

        async with session:
            await plugin.attach(session)

            # Register a username
            await plugin.register("alice")

            # Set up event handlers
            def on_incoming_call(data):
                print(f"Incoming call from {data['username']}")
                # Handle incoming call...

            plugin.on_event(VideoCallEventType.INCOMINGCALL, on_incoming_call)

            # Make a call
            player = MediaPlayer("input.mp4")
            recorder = MediaRecorder("output.mp4")
            await plugin.call("bob", player, recorder)

            await plugin.destroy()
        ```
    """

    name = "janus.plugin.videocall"

    def __init__(self, **kwargs) -> None:
        """Initialize the VideoCall plugin.

        Args:
            **kwargs: Keyword arguments passed to JanusPlugin constructor.
                Supports pc_config parameter for WebRTC configuration.

        Examples:
            Basic usage:
            ```python
            plugin = JanusVideoCallPlugin()
            ```

            With WebRTC configuration:
            ```python
            from aiortc import RTCConfiguration, RTCIceServer

            config = RTCConfiguration(iceServers=[
                RTCIceServer(urls='stun:stun.l.google.com:19302')
            ])
            plugin = JanusVideoCallPlugin(pc_config=config)
            ```
        """
        super().__init__(**kwargs)
        self._username: Optional[str] = None
        self._player: Optional[MediaPlayer] = None
        self._recorder: Optional[MediaRecorder] = None
        self._in_call = False
        self._webrtcup_event = asyncio.Event()
        self._event_handlers: Dict[
            VideoCallEventType, List[Callable[[Any], Awaitable]]
        ] = {event_type: [] for event_type in VideoCallEventType}

    @property
    def username(self) -> Optional[str]:
        """Get the registered username."""
        return self._username

    @property
    def in_call(self) -> bool:
        """Check if currently in a call."""
        return self._in_call

    def on_event(
        self,
        event_type: VideoCallEventType,
        handler: Callable[[Dict[str, Any]], Awaitable],
    ) -> None:
        """Register an event handler for VideoCall events.

        Args:
            event_type: The type of event to handle.
            handler: Callback function to handle the event.
        """
        self._event_handlers[event_type].append(handler)

    async def _trigger_event(
        self, event_type: VideoCallEventType, data: Dict[str, Any]
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

    async def on_receive(self, response: Dict[str, Any]) -> None:
        """Handle incoming messages from Janus.

        Args:
            response: The response message from Janus.
        """
        if "jsep" in response and response["jsep"]["type"] == "answer":
            await self.on_receive_jsep(jsep=response["jsep"])

        janus_code = response["janus"]

        if janus_code == "webrtcup":
            logger.info("WebRTC connection established")
            self._webrtcup_event.set()

        elif janus_code == "hangup":
            logger.info("WebRTC connection closed")
            self._in_call = False
            if self.pc.signalingState != "closed":
                await self.pc.close()

        elif janus_code == "media":
            if "receiving" in response and response["receiving"] and self._recorder:
                # Start recording when media is received
                await self._recorder.start()

        elif janus_code == "event":
            await self._handle_event(response)

    async def _handle_event(self, response: Dict[str, Any]) -> None:
        """Handle plugin events.

        Args:
            response: The event response from Janus.
        """
        if "plugindata" not in response:
            return

        plugin_data = response["plugindata"]["data"]
        if plugin_data["videocall"] != "event":
            return

        result = plugin_data["result"]
        event_type = result["event"]

        if event_type == "registered":
            await self._trigger_event(VideoCallEventType.REGISTERED, result)

        elif event_type == "calling":
            await self._trigger_event(VideoCallEventType.CALLING, result)

        elif event_type == "incomingcall":
            self._in_call = True
            # Include JSEP data if present
            event_data = result.copy()
            if "jsep" in response:
                event_data["jsep"] = response["jsep"]
            await self._trigger_event(VideoCallEventType.INCOMINGCALL, event_data)

        elif event_type == "accepted":
            self._in_call = True
            await self._trigger_event(VideoCallEventType.ACCEPTED, result)

        elif event_type == "update":
            # Include JSEP data if present
            event_data = result.copy()
            if "jsep" in response:
                event_data["jsep"] = response["jsep"]
            await self._trigger_event(VideoCallEventType.UPDATE, event_data)

        elif event_type == "hangup":
            self._in_call = False
            await self._trigger_event(VideoCallEventType.HANGUP, result)

        elif event_type == "set":
            await self._trigger_event(VideoCallEventType.SET, result)

    def _check_error_in_response(self, response: Dict[str, Any]) -> None:
        """Check for errors in response and raise VideoCallError if found.

        Args:
            response: The response to check for errors.

        Raises:
            VideoCallError: If an error is found in the response.
        """
        if is_subset(response, {"janus": "error", "error": {}}):
            error: Dict = response["error"]
            raise VideoCallError(
                error.get("code", 0), error.get("reason", "Unknown error")
            )

        if is_subset(
            response,
            {
                "janus": "event",
                "plugindata": {
                    "plugin": self.name,
                    "data": {"videocall": "event", "error_code": None, "error": None},
                },
            },
        ):
            plugin_data = response["plugindata"]["data"]
            error_code: int = plugin_data["error_code"]
            error_message: str = plugin_data["error"]
            raise VideoCallError(error_code, error_message)

    async def _send_request(
        self,
        body: Dict[str, Any],
        jsep: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Send a request to the VideoCall plugin.

        Args:
            body: The request body.
            jsep: Optional JSEP data to include.
            timeout: Request timeout in seconds.

        Returns:
            The response from the plugin.

        Raises:
            VideoCallError: If the request fails.
            TimeoutError: If the request times out.
        """

        def response_matcher(response: Dict[str, Any]) -> bool:
            return is_subset(
                response,
                {
                    "janus": "event",
                    "plugindata": {
                        "plugin": self.name,
                        "data": {"videocall": "event"},
                    },
                },
            ) or is_subset(response, {"janus": "error", "error": {}})

        message = {"janus": "message", "body": body}
        if jsep:
            message["jsep"] = jsep

        message_transaction = await self.send(message)
        response = await message_transaction.get(
            matcher=response_matcher, timeout=timeout
        )
        await message_transaction.done()

        self._check_error_in_response(response)
        return response

    async def list_users(self, timeout: float = 15.0) -> List[str]:
        """List all registered users.

        Args:
            timeout: Request timeout in seconds.

        Returns:
            List of registered usernames.

        Raises:
            VideoCallError: If the request fails.
            TimeoutError: If the request times out.
        """
        response = await self._send_request(body={"request": "list"}, timeout=timeout)

        return response["plugindata"]["data"]["result"]["list"]

    async def register(self, username: str, timeout: float = 15.0) -> bool:
        """Register a username for receiving calls.

        Args:
            username: The username to register.
            timeout: Request timeout in seconds.

        Returns:
            True if registration was successful.

        Raises:
            VideoCallError: If registration fails.
            TimeoutError: If the request times out.
        """
        if self._username:
            raise VideoCallError(0, f"Already registered as '{self._username}'")

        response = await self._send_request(
            body={"request": "register", "username": username}, timeout=timeout
        )

        matcher_success = {
            "janus": "event",
            "plugindata": {
                "plugin": self.name,
                "data": {
                    "videocall": "event",
                    "result": {
                        "event": "registered",
                    },
                },
            },
        }

        if is_subset(response, matcher_success):
            self._username = username
            return True

        return False

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
                logger.info(f"{self.username}: Received {track.kind} track")
                recorder.addTrack(track)

        self._player = player
        self._recorder = recorder

    async def call(
        self,
        username: str,
        player: Optional[MediaPlayer] = None,
        recorder: Optional[MediaRecorder] = None,
        trickle: bool = False,
        timeout: float = 30.0,
    ) -> bool:
        """Initiate a call to another user.

        Args:
            username: The username to call.
            player: Media player for outgoing media.
            recorder: Media recorder for incoming media.
            trickle: Whether to use trickle ICE.
            timeout: Request timeout in seconds.

        Returns:
            True if the call was initiated successfully.

        Raises:
            VideoCallError: If the call fails.
            TimeoutError: If the request times out.
        """
        if not self._username:
            raise VideoCallError(0, "Must register a username first")

        if self._in_call:
            raise VideoCallError(0, "Already in a call")

        # Set up media
        self._setup_media_tracks(player, recorder)

        # Create offer
        await self.pc.setLocalDescription(await self.pc.createOffer())
        jsep = await self.create_jsep(self.pc, trickle=trickle)

        response = await self._send_request(
            body={"request": "call", "username": username},
            jsep=jsep,
            timeout=timeout,
        )

        matcher_success = {
            "janus": "event",
            "plugindata": {
                "plugin": self.name,
                "data": {
                    "videocall": "event",
                    "result": {
                        "event": "calling",
                    },
                },
            },
        }

        return is_subset(response, matcher_success)

    async def accept(
        self,
        jsep: Dict[str, str],
        player: Optional[MediaPlayer] = None,
        recorder: Optional[MediaRecorder] = None,
        trickle: bool = False,
        timeout: float = 30.0,
    ) -> bool:
        """Accept an incoming call.

        Args:
            player: Media player for outgoing media.
            recorder: Media recorder for incoming media.
            trickle: Whether to use trickle ICE.
            timeout: Request timeout in seconds.

        Returns:
            True if the call was accepted successfully.

        Raises:
            VideoCallError: If accepting the call fails.
            TimeoutError: If the request times out.
        """
        if not self._username:
            raise VideoCallError(0, "Must register a username first")

        if not self._in_call:
            raise VideoCallError(0, "No incoming call to accept")

        # Set up media
        self._setup_media_tracks(player, recorder)

        await self.pc.setRemoteDescription(
            RTCSessionDescription(sdp=jsep["sdp"], type=jsep["type"])
        )

        # sdp_answer = await self.pc.createAnswer()

        await self.pc.setLocalDescription(await self.pc.createAnswer())

        jsep_answer = await self.create_jsep(self.pc, trickle=trickle)
        # jsep_answer = {
        #     "sdp": sdp_answer.sdp,
        #     # Not sure if should follow received trickle in JSEP or not
        #     "trickle": trickle,
        #     "type": sdp_answer.type,
        # }

        response = await self._send_request(
            body={"request": "accept"}, jsep=jsep_answer, timeout=timeout
        )

        matcher_success = {
            "janus": "event",
            "plugindata": {
                "plugin": self.name,
                "data": {
                    "videocall": "event",
                    "result": {
                        "event": "accepted",
                    },
                },
            },
        }

        return is_subset(response, matcher_success)

    async def set_media(
        self,
        audio: Optional[bool] = None,
        video: Optional[bool] = None,
        bitrate: Optional[int] = None,
        record: Optional[bool] = None,
        filename: Optional[str] = None,
        substream: Optional[int] = None,
        temporal: Optional[int] = None,
        fallback: Optional[int] = None,
        jsep: Optional[Dict[str, Any]] = None,
        timeout: float = 15.0,
    ) -> bool:
        """Configure media settings for the call.

        Args:
            audio: Enable/disable audio.
            video: Enable/disable video.
            bitrate: Bitrate limit in bps.
            record: Enable/disable recording.
            filename: Base filename for recording.
            substream: Substream to receive (0-2) for simulcast.
            temporal: Temporal layers to receive (0-2) for simulcast.
            fallback: Fallback time in microseconds for simulcast.
            jsep: Optional JSEP for renegotiation.
            timeout: Request timeout in seconds.

        Returns:
            True if settings were applied successfully.

        Raises:
            VideoCallError: If the request fails.
            TimeoutError: If the request times out.
        """
        body: Dict[str, Any] = {"request": "set"}

        if audio is not None:
            body["audio"] = audio
        if video is not None:
            body["video"] = video
        if bitrate is not None:
            body["bitrate"] = bitrate
        if record is not None:
            body["record"] = record
        if filename is not None:
            body["filename"] = filename
        if substream is not None:
            body["substream"] = substream
        if temporal is not None:
            body["temporal"] = temporal
        if fallback is not None:
            body["fallback"] = fallback

        response = await self._send_request(body=body, jsep=jsep, timeout=timeout)

        matcher_success = {
            "janus": "event",
            "plugindata": {
                "plugin": self.name,
                "data": {
                    "videocall": "event",
                    "result": {
                        "event": "set",
                    },
                },
            },
        }

        return is_subset(response, matcher_success)

    async def hangup(self, timeout: float = 15.0) -> bool:
        """Hang up the current call.

        Args:
            timeout: Request timeout in seconds.

        Returns:
            True if hangup was successful.

        Raises:
            VideoCallError: If the request fails.
            TimeoutError: If the request times out.
        """
        response = await self._send_request(body={"request": "hangup"}, timeout=timeout)

        # Clean up resources
        self._in_call = False
        await self._cleanup_media()

        matcher_success = {
            "janus": "event",
            "plugindata": {
                "plugin": self.name,
                "data": {
                    "videocall": "event",
                    "result": {
                        "event": "hangup",
                    },
                },
            },
        }

        return is_subset(response, matcher_success)

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

        # Reset peer connection
        if self.pc.signalingState != "closed":
            await self.reset_connection()

    async def destroy(self) -> None:
        """Destroy the plugin and clean up all resources."""
        # Clean up media first
        await self._cleanup_media()

        # Clear state
        self._username = None
        self._in_call = False
        self._webrtcup_event.clear()

        # Call parent destroy
        await super().destroy()
