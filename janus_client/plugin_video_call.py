import logging
import asyncio

from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    # VideoStreamTrack,
    MediaStreamTrack,
)
from aiortc.contrib.media import MediaPlayer, MediaRecorder

from .plugin_base import JanusPlugin
from .message_transaction import is_subset

logger = logging.getLogger(__name__)


class JanusVideoCallPlugin(JanusPlugin):
    """Janus Video Call plugin implementation"""

    name = "janus.plugin.videocall"  #: Plugin name
    __username: str
    __pc: RTCPeerConnection

    def __init__(self) -> None:
        super().__init__()

        self.__username = ""
        self.__pc = None
        self.__recorder = None
        self.player = None

    async def on_receive(self, response: dict):
        # Handle JSEP. Could be answer or offer.
        if "jsep" in response and response["jsep"]["type"] == "answer":
            await self.on_receive_jsep(response["jsep"])

        janus_code = response["janus"]

        if janus_code == "media":
            if response["receiving"]:
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
                        asyncio.create_task(self.on_incoming_call(response))
        else:
            logger.info(f"Unimplemented response handle: {response}")

    async def on_receive_jsep(self, jsep: dict):
        if self.__pc and self.__pc.signalingState != "closed":
            await self.__pc.setRemoteDescription(
                RTCSessionDescription(sdp=jsep["sdp"], type=jsep["type"])
            )

    async def on_incoming_call(self, response: dict):
        self.__pc = RTCPeerConnection()
        self.player = MediaPlayer("./Into.the.Wild.2007.mp4")

        jsep = response["jsep"]
        await self.__pc.setRemoteDescription(
            RTCSessionDescription(sdp=jsep["sdp"], type=jsep["type"])
        )

        # configure media
        if self.player.audio:
            self.__pc.addTrack(self.player.audio)

        if self.player.video:
            self.__pc.addTrack(self.player.video)

        recorder = MediaRecorder("./videocall_in_record.mp4")

        if recorder:
            self.__recorder = recorder

            @self.__pc.on("track")
            async def on_track(track: MediaStreamTrack):
                logger.info("Track %s received" % track.kind)
                if track.kind == "video":
                    self.__recorder.addTrack(track)
                if track.kind == "audio":
                    self.__recorder.addTrack(track)

        await self.__pc.setLocalDescription(await self.__pc.createAnswer())
        jsep = {
            "sdp": self.__pc.localDescription.sdp,
            "trickle": False,
            "type": self.__pc.localDescription.type,
        }
        await self.accept(jsep=jsep)

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
        self.__pc = RTCPeerConnection()

        # configure media
        if player.audio:
            self.__pc.addTrack(player.audio)

        if player.video:
            self.__pc.addTrack(player.video)

        if recorder:
            self.__recorder = recorder

            @self.__pc.on("track")
            async def on_track(track: MediaStreamTrack):
                logger.info("Track %s received" % track.kind)
                if track.kind == "video":
                    self.__recorder.addTrack(track)
                if track.kind == "audio":
                    self.__recorder.addTrack(track)

            await recorder.start()

        # send offer
        await self.__pc.setLocalDescription(await self.__pc.createOffer())

        jsep = {
            "sdp": self.__pc.localDescription.sdp,
            "trickle": True,
            "type": self.__pc.localDescription.type,
        }

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

    async def accept(self, jsep: dict) -> bool:
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

        # Stream ended. Ok to close PC multiple times.
        if self.__pc:
            await self.__pc.close()
        # Ok to stop recording multiple times.
        if self.__recorder:
            await self.__recorder.stop()

        return is_subset(response, matcher_success)
