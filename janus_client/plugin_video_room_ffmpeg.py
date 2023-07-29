import asyncio
import logging

from .plugin_base import JanusPlugin, PluginMessage
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from .media import MediaPlayer

logger = logging.getLogger(__name__)


class JanusVideoRoomPlugin(JanusPlugin):
    """Janus VideoRoom plugin instance

    Implements API to interact with VideoRoom plugin.

    Each plugin instance is expected to have only 1 PeerConnection
    """

    name = "janus.plugin.videoroom"  #: Plugin name
    pc = RTCPeerConnection()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.joined_event = asyncio.Event()
        self.loop = asyncio.get_running_loop()

    def handle_async_response(self, response: dict):
        if response["janus"] == "event":
            logger.info(f"Event response: {response}")
            if "plugindata" in response:
                if response["plugindata"]["data"]["videoroom"] == "attached":
                    # Subscriber attached
                    self.joined_event.set()
                elif response["plugindata"]["data"]["videoroom"] == "joined":
                    # Participant joined (joined as publisher but may not publish)
                    self.joined_event.set()
        else:
            logger.info(f"Unimplemented response handle: {response['janus']}")
            logger.info(response)

        # Handle JSEP. Could be answer or offer.
        if "jsep" in response:
            asyncio.create_task(self.handle_jsep(response["jsep"]))

    async def join(self, room_id: int, publisher_id: int, display_name: str) -> None:
        """Join a room

        | A handle can join a room and then do nothing, but this should be called before publishing.
        | There is an API to configure and publish at the same time, but it's not implemented yet.

        :param room_id: Room ID to join. This must be available at the server.
        :param publisher_id: Your publisher ID to set.
        :param display_name: Your display name when you join the room.
        """

        class JoinMessage(PluginMessage):
            body: dict

        response = await self.send(
            JoinMessage(
                janus="message",
                body={
                    "request": "join",
                    "ptype": "publisher",
                    "room": room_id,
                    "id": publisher_id,
                    "display": display_name,
                },
            )
        )
        logger.info(f"Room join response: {response}")
        await self.joined_event.wait()

    async def leave(self):
        class LeaveMessage(PluginMessage):
            body: dict

        response = await self.send(
            LeaveMessage(
                janus="message",
                body={
                    "request": "leave",
                },
            )
        )
        logger.info(f"Room leave response: {response}")

    async def publish(self, ffmpeg_input, width: int, height: int) -> None:
        """Publish video stream to the room

        Should already have joined a room before this. Then this will publish the
        video stream to the handle.
        """

        # create media source
        player = MediaPlayer(
            ffmpeg_input,
            width,
            height,
        )
        # Just save the media player. Not used
        self.player = player

        # configure media
        media = {"audio": False, "video": True}
        if player and player.audio:
            self.pc.addTrack(player.audio)
            media["audio"] = True

        if player and player.video:
            self.pc.addTrack(player.video)
        else:
            self.pc.addTrack(VideoStreamTrack())

        # send offer
        await self.pc.setLocalDescription(await self.pc.createOffer())

        request = {"request": "configure"}
        request.update(media)

        class PublishMessage(PluginMessage):
            body: dict
            jsep: dict

        await self.send(
            PublishMessage(
                janus="message",
                body=request,
                jsep={
                    "sdp": self.pc.localDescription.sdp,
                    "trickle": False,
                    "type": self.pc.localDescription.type,
                },
            )
        )

        await self.joined_event.wait()

    async def unpublish(self) -> None:
        """Stop publishing"""

        class UnpublishMessage(PluginMessage):
            body: dict

        await self.send(
            UnpublishMessage(
                janus="message",
                body={
                    "request": "unpublish",
                },
            )
        )
        await self.pc.close()

    async def subscribe(self, room_id: int, feed_id: int) -> None:
        """Subscribe to a feed

        :param room_id: Room ID containing the feed. The same ID that
            you would use to join the room.
        :param feed_id: ID of the feed that you want to stream. Should be their publisher ID.
        """

        await self.send(
            {
                "janus": "message",
                "body": {
                    "request": "join",
                    "ptype": "subscriber",
                    "room": room_id,
                    "feed": feed_id,
                    # "close_pc": True,
                    # "audio": True,
                    # "video": True,
                    # "data": True,
                    # "offer_audio": True,
                    # "offer_video": True,
                    # "offer_data": True,
                },
            }
        )
        await self.joined_event.wait()

    async def unsubscribe(self) -> None:
        """Unsubscribe from the feed"""

        await self.send(
            {
                "janus": "message",
                "body": {
                    "request": "leave",
                },
            }
        )
        self.joined_event.clear()

    async def start(self, answer=None) -> None:
        """Signal WebRTC start. I guess"""

        payload = {"janus": "message", "body": {"request": "start"}}
        if answer:
            payload["jsep"] = {
                "sdp": answer,
                "type": "answer",
                "trickle": True,
            }
        await self.send(payload)

    async def pause(self) -> None:
        """Pause media streaming"""

        await self.send(
            {
                "janus": "message",
                "body": {
                    "request": "pause",
                },
            }
        )

    async def list_participants(self, room_id: int) -> list:
        """Get participant list

        Get a list of publishers in the room, that are currently publishing.

        :param room_id: List participants in this room
        :return: A list containing the participants. Can be empty.
        """

        response = await self.send(
            {
                "janus": "message",
                "body": {
                    "request": "listparticipants",
                    "room": room_id,
                },
            }
        )
        return response["plugindata"]["data"]["participants"]

    async def handle_jsep(self, jsep):
        logger.info(jsep)
        if "sdp" in jsep:
            sdp = jsep["sdp"]
            if jsep["type"] == "answer":
                logger.info(f"Received answer:\n{sdp}")

                # apply answer
                await self.pc.setRemoteDescription(
                    RTCSessionDescription(sdp=jsep["sdp"], type=jsep["type"])
                )
            elif jsep["type"] == "offer":
                pass
            else:
                raise Exception("Invalid JSEP")

        elif "ice" in jsep:
            ice = jsep["ice"]
            candidate = ice["candidate"]
            sdpMLineIndex = ice["sdpMLineIndex"]
            self.webrtcbin.emit("add-ice-candidate", sdpMLineIndex, candidate)
