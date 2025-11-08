import logging
import asyncio
from typing import Optional

from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    MediaStreamTrack,
)
from aiortc.contrib.media import MediaPlayer, MediaRecorder

from .plugin_base import JanusPlugin
from .message_transaction import is_subset

logger = logging.getLogger(__name__)


class JanusVideoCallPlugin(JanusPlugin):
    """Janus Video Call plugin implementation.

    The peer connection can be configured with STUN/TURN servers for NAT traversal.

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

    name = "janus.plugin.videocall"  #: Plugin name
    __username: str
    __player: Optional[MediaPlayer]
    __recorder: Optional[MediaRecorder]

    def __init__(self, **kwargs) -> None:
        """Initialize the VideoCall plugin.

        Args:
            **kwargs: Keyword arguments passed to JanusPlugin constructor.
                Supports pc_config parameter for WebRTC configuration.
        """
        super().__init__(**kwargs)

        self.__username = ""
        self.__player = None
        self.__recorder = None

    async def on_receive(self, response: dict):
        # Handle JSEP. Could be answer or offer.
        if "jsep" in response and response["jsep"]["type"] == "answer":
            await self.on_receive_jsep(response["jsep"])

        janus_code = response["janus"]

        if janus_code == "media":
            if response["receiving"] and self.__recorder:
                # It's ok to start multiple times, only the track that
                # has not been started will start
                await self.__recorder.start()

        if janus_code == "event":
            logger.info(f"Event response: {response}")
            if "plugindata" in response:
                if response["plugindata"]["data"]["videocall"] == "event":
                    event_result = response["plugindata"]["data"]["result"]
                    logger.info(f"Event result: {event_result}")
                    if (
                        "event" in event_result
                        and event_result["event"] == "incomingcall"
                    ):
                        asyncio.create_task(
                            self.on_incoming_call(jsep=response["jsep"])
                        )
        else:
            logger.info(f"Unimplemented response handle: {response}")

    async def on_receive_jsep(self, jsep: dict):
        if self.pc.signalingState != "closed":
            await self.pc.setRemoteDescription(
                RTCSessionDescription(sdp=jsep["sdp"], type=jsep["type"])
            )

    async def create_pc(
        self, player: MediaPlayer, recorder: MediaRecorder = None, jsep: dict = {}
    ) -> RTCPeerConnection:
        pc = RTCPeerConnection()

        # configure media
        if player.audio:
            pc.addTrack(player.audio)

        if player.video:
            pc.addTrack(player.video)

        # Must configure on track event before setRemoteDescription
        if recorder:

            @pc.on("track")
            async def on_track(track: MediaStreamTrack):
                logger.info("Track %s received" % track.kind)
                if track.kind == "video":
                    recorder.addTrack(track)
                if track.kind == "audio":
                    recorder.addTrack(track)

        if jsep:
            await pc.setRemoteDescription(
                RTCSessionDescription(sdp=jsep["sdp"], type=jsep["type"])
            )

        return pc

    async def on_incoming_call(self, jsep: dict):
        """Override this. This will be called when plugin receive incoming call event"""
        pass
        # # self.__player = MediaPlayer("./Into.the.Wild.2007.mp4")
        # self.__player = MediaPlayer("http://download.tsi.telecom-paristech.fr/gpac/dataset/dash/uhd/mux_sources/hevcds_720p30_2M.mp4")
        # self.__recorder = MediaRecorder("./videocall_in_record.mp4")
        # self.__pc = await self.create_pc(
        #     player=self.__player,
        #     recorder=self.__recorder,
        #     jsep=jsep,
        # )

        # await self.__pc.setLocalDescription(await self.__pc.createAnswer())
        # jsep = {
        #     "sdp": self.__pc.localDescription.sdp,
        #     "trickle": False,
        #     "type": self.__pc.localDescription.type,
        # }
        # await self.accept(jsep=jsep)

    async def send_wrapper(self, message: dict, matcher: dict, jsep: dict = {}) -> dict:
        def function_matcher(message: dict):
            return is_subset(message, matcher) or is_subset(
                message,
                {
                    "janus": "event",
                    "plugindata": {
                        "plugin": "janus.plugin.videocall",
                        "data": {
                            "videocall": "event",
                            "error_code": None,
                            "error": None,
                        },
                    },
                },
            )

        full_message = message
        if jsep:
            full_message = {**message, "jsep": jsep}

        message_transaction = await self.send(
            message=full_message,
        )
        response = await message_transaction.get(matcher=function_matcher)
        await message_transaction.done()

        return response

    async def list(self) -> list:
        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": {
                    "request": "list",
                },
            },
            matcher={
                "janus": "event",
                "plugindata": {
                    "plugin": "janus.plugin.videocall",
                    "data": {"videocall": "event", "result": {"list": None}},
                },
            },
        )

        return response["plugindata"]["data"]["result"]["list"]

    async def register(self, username: str) -> bool:
        """Register a username

        Detach plugin to de-register the username
        """
        if self.__username:
            raise Exception(f"Can only register 1 username: {self.__username}")

        matcher_success = {
            "janus": "event",
            "plugindata": {
                "plugin": "janus.plugin.videocall",
                "data": {
                    "videocall": "event",
                    "result": {
                        "event": "registered",
                    },
                },
            },
        }
        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": {
                    "request": "register",
                    "username": username,
                },
            },
            matcher=matcher_success,
        )

        if is_subset(response, matcher_success):
            self.__username = username
            return True
        else:
            return False

    async def call(
        self, username: str, player: MediaPlayer, recorder: MediaRecorder = None
    ) -> bool:
        if not self.__username:
            raise Exception("Register a username first")

        # Configure media on the base class peer connection
        if player.audio:
            self.pc.addTrack(player.audio)
        if player.video:
            self.pc.addTrack(player.video)

        # Set up track handler for recording
        if recorder:

            @self.pc.on("track")
            async def on_track(track: MediaStreamTrack):
                logger.info("Track %s received" % track.kind)
                if track.kind == "video":
                    recorder.addTrack(track)
                if track.kind == "audio":
                    recorder.addTrack(track)

        self.__player = player
        self.__recorder = recorder

        # send offer
        await self.pc.setLocalDescription(await self.pc.createOffer())

        jsep = await self.create_jsep(pc=self.pc, trickle=True)

        matcher_success = {
            "janus": "event",
            "plugindata": {
                "plugin": "janus.plugin.videocall",
                "data": {
                    "videocall": "event",
                    "result": {
                        "event": "calling",
                    },
                },
            },
        }
        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": {
                    "request": "call",
                    "username": username,
                },
            },
            matcher=matcher_success,
            jsep=jsep,
        )

        return is_subset(response, matcher_success)

    async def accept(
        self,
        jsep: dict,
        player: MediaPlayer,
        recorder: Optional[MediaRecorder] = None,
    ) -> bool:
        # Configure media on the base class peer connection
        if player.audio:
            self.pc.addTrack(player.audio)
        if player.video:
            self.pc.addTrack(player.video)

        # Set up track handler for recording
        if recorder:

            @self.pc.on("track")
            async def on_track(track: MediaStreamTrack):
                logger.info("Track %s received" % track.kind)
                if track.kind == "video":
                    recorder.addTrack(track)
                if track.kind == "audio":
                    recorder.addTrack(track)

        self.__player = player
        self.__recorder = recorder

        matcher_success = {
            "janus": "event",
            "plugindata": {
                "plugin": "janus.plugin.videocall",
                "data": {
                    "videocall": "event",
                    "result": {
                        "event": "accepted",
                    },
                },
            },
        }
        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": {
                    "request": "accept",
                },
            },
            matcher=matcher_success,
            jsep=jsep,
        )

        return is_subset(response, matcher_success)

    async def set(self, audio: bool, video: bool, jsep: dict = {}) -> bool:
        matcher_success = {
            "janus": "event",
            "plugindata": {
                "plugin": "janus.plugin.videocall",
                "data": {
                    "videocall": "event",
                    "result": {
                        "event": "set",
                    },
                },
            },
        }
        body = {
            "request": "set",
            "audio": audio,
            "video": video,
            # "bitrate" : <numeric bitrate value>,
            # "record" : true|false,
            # "filename" : <base path/filename to use for the recording>,
            # "substream" : <substream to receive (0-2), in case simulcasting is enabled>,
            # "temporal" : <temporal layers to receive (0-2), in case simulcasting is enabled>,
            # "fallback" : <How much time (in us, default 250000) without receiving packets will make us drop to the substream below>
        }
        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": body,
            },
            matcher=matcher_success,
            jsep=jsep,
        )

        return is_subset(response, matcher_success)

    async def hangup(self) -> bool:
        matcher_success = {
            "janus": "event",
            "plugindata": {
                "plugin": "janus.plugin.videocall",
                "data": {
                    "videocall": "event",
                    "result": {
                        "event": "hangup",
                    },
                },
            },
        }
        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": {
                    "request": "hangup",
                },
            },
            matcher=matcher_success,
        )

        # Stream ended.
        await self.reset_connection()

        # Ok to stop recording multiple times.
        if self.__recorder:
            await self.__recorder.stop()
            self.__recorder = None
        self.__player = None

        return is_subset(response, matcher_success)
