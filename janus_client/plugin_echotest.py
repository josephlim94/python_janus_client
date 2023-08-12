# import asyncio
import logging

from .plugin_base import JanusPlugin
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaPlayer

logger = logging.getLogger(__name__)


class JanusEchoTestPlugin(JanusPlugin):
    """Janus EchoTest plugin implementation"""

    name = "janus.plugin.echotest"
    __pc: RTCPeerConnection

    def on_receive(self, response: dict):
        logger.info(f"EchoTest received: {response}")

    async def start(self):
        self.__pc = RTCPeerConnection()

        player = MediaPlayer("C:\\Users\\Joseph\\Downloads\\De Kandar Demo.mp4")

        # configure media
        media = {"audio": False, "video": True}
        if player and player.audio:
            self.__pc.addTrack(player.audio)
            media["audio"] = True

        if player and player.video:
            self.__pc.addTrack(player.video)
        else:
            self.__pc.addTrack(VideoStreamTrack())

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

        response = await self.send(message)

        # apply answer
        # await self.__pc.setRemoteDescription(
        #     RTCSessionDescription(
        #         sdp=response["jsep"]["sdp"], type=response["jsep"]["type"]
        #     )
        # )
