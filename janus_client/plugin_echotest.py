import asyncio
import logging

from .plugin_base import JanusPlugin
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaPlayer, MediaRecorder

logger = logging.getLogger(__name__)


class JanusEchoTestPlugin(JanusPlugin):
    """Janus EchoTest plugin implementation"""

    name = "janus.plugin.echotest"
    __pc: RTCPeerConnection
    __recorder: MediaRecorder
    __webrtcup_event: asyncio.Event

    def __init__(self) -> None:
        super().__init__()

        self.__webrtcup_event = asyncio.Event()

    async def on_receive(self, response: dict):
        if "jsep" in response:
            await self.on_receive_jsep(jsep=response["jsep"])

        janus_code = response["janus"]

        if janus_code == "media":
            if response["receiving"]:
                # It's ok to start multiple times, only the track that
                # has not been started will start
                await self.__recorder.start()

        if janus_code == "webrtcup":
            self.__webrtcup_event.set()

        if janus_code == "event":
            plugin_data = response["plugindata"]["data"]

            if plugin_data["echotest"] != "event":
                # This plugin will only get events
                logger.error(f"Invalid response: {response}")
                return

            if "result" in plugin_data:
                if plugin_data["result"] == "ok":
                    # Successful start stream request. Do nothing.
                    pass

                if plugin_data["result"] == "done":
                    # Stream ended. Ok to close PC multiple times.
                    if self.__pc:
                        await self.__pc.close()
                    # Ok to stop recording multiple times.
                    if self.__recorder:
                        await self.__recorder.stop()

            if "errorcode" in plugin_data:
                logger.error(f"Plugin Error: {response}")

    async def wait_webrtcup(self) -> None:
        await self.__webrtcup_event.wait()
        self.__webrtcup_event.clear()

    async def on_receive_jsep(self, jsep: dict):
        if self.__pc and self.__pc.signalingState != "closed":
            await self.__pc.setRemoteDescription(
                RTCSessionDescription(sdp=jsep["sdp"], type=jsep["type"])
            )

    async def start(self, play_from: str, record_to: str = ""):
        self.__pc = RTCPeerConnection()

        player = MediaPlayer(play_from)

        # configure media
        if player and player.audio:
            self.__pc.addTrack(player.audio)

        if player and player.video:
            self.__pc.addTrack(player.video)
        else:
            self.__pc.addTrack(VideoStreamTrack())

        if record_to:
            self.__recorder = MediaRecorder(record_to)

            @self.__pc.on("track")
            async def on_track(track):
                logger.info("Track %s received" % track.kind)
                if track.kind == "video":
                    self.__recorder.addTrack(track)
                if track.kind == "audio":
                    self.__recorder.addTrack(track)

        # send offer
        await self.__pc.setLocalDescription(await self.__pc.createOffer())

        message = {"janus": "message"}
        body = {
            "audio": bool(player.audio),
            # "audiocodec" : "<optional codec name; only used when creating a PeerConnection>",
            "video": bool(player.video),
            # "videocodec" : "<optional codec name; only used when creating a PeerConnection>",
            # "videoprofile" : "<optional codec profile to force; only used when creating a PeerConnection, only valid for VP9 (0 or 2) and H.264 (e.g., 42e01f)>",
            # "bitrate" : <numeric bitrate value>,
            # "record" : true|false,
            # "filename" : <base path/filename to use for the recording>,
            # "substream" : <substream to receive (0-2), in case simulcasting is enabled>,
            # "temporal" : <temporal layers to receive (0-2), in case simulcasting is enabled>,
            # "svc" : true|false,
            # "spatial_layer" : <spatial layer to receive (0-2), in case SVC is enabled>,
            # "temporal_layer" : <temporal layers to receive (0-2), in case SVC is enabled>
        }
        message["body"] = body
        message["jsep"] = {
            "sdp": self.__pc.localDescription.sdp,
            "trickle": False,
            "type": self.__pc.localDescription.type,
        }

        message_transaction = await self.send(message)
        response = await message_transaction.get()
        await message_transaction.done()

        # Immediately apply answer if it's found
        if "jsep" in response:
            await self.on_receive_jsep(jsep=response["jsep"])

    async def close_stream(self):
        """Close stream

        This should cause the stream to stop and a done event to be received.
        """
        if self.__pc:
            await self.__pc.close()

        if self.__recorder:
            await self.__recorder.stop()
