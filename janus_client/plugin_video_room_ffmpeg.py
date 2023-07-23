from janus_client import JanusPlugin
import asyncio
import logging
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from .media import MediaPlayer

logger = logging.getLogger(__name__)


class JanusVideoRoomPlugin(JanusPlugin):
    """Janus VideoRoom plugin instance

    Implements API to interact with VideoRoom plugin.
    """

    name = "janus.plugin.videoroom"  #: Plugin name
    pc = RTCPeerConnection()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.joined_event = asyncio.Event()
        self.gst_webrtc_ready = asyncio.Event()
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

        await self.send(
            {
                "janus": "message",
                "body": {
                    "request": "join",
                    "ptype": "publisher",
                    "room": room_id,
                    "id": publisher_id,
                    "display": display_name,
                },
            }
        )
        await self.joined_event.wait()

    async def publish(self, player: MediaPlayer) -> None:
        """Publish video stream to the room

        Should already have joined a room before this. Then this will publish the
        video stream to the handle.
        """

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
        await self.send(
            {
                "janus": "message",
                "body": request,
                "jsep": {
                    "sdp": self.pc.localDescription.sdp,
                    "trickle": False,
                    "type": self.pc.localDescription.type,
                },
            }
        )

        # text = offer.sdp.as_text()
        # logger.info("Sending offer and publishing:\n%s" % text)
        # await self.send(
        #     {
        #         "janus": "message",
        #         "body": {
        #             "request": "publish",
        #             "audio": True,
        #             "video": True,
        #         },
        #         "jsep": {
        #             "sdp": text,
        #             "type": "offer",
        #             "trickle": True,
        #         },
        #     }
        # )
        await self.joined_event.wait()

    async def unpublish(self) -> None:
        """Stop publishing"""
        await self.send(
            {
                "janus": "message",
                "body": {
                    "request": "unpublish",
                },
            }
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

    def on_negotiation_needed(self, element):
        logger.info("on_negotiation_needed called")
        self.gst_webrtc_ready.set()
        # promise = Gst.Promise.new_with_change_func(self.on_offer_created, element, None)
        # element.emit('create-offer', None, promise)

    def send_ice_candidate_message(self, _, sdpMLineIndex, candidate):
        icemsg = {"candidate": candidate, "sdpMLineIndex": sdpMLineIndex}
        logger.info(f"Sending ICE {icemsg}")
        # loop = asyncio.new_event_loop()
        future = asyncio.run_coroutine_threadsafe(
            self.trickle(sdpMLineIndex, candidate), self.loop
        )
        future.result()

    def extract_ice_from_sdp(self, sdp):
        mlineindex = -1
        for line in sdp.splitlines():
            if line.startswith("a=candidate"):
                candidate = line[2:]
                if mlineindex < 0:
                    logger.info("Received ice candidate in SDP before any m= line")
                    continue
                logger.info(
                    "Received remote ice-candidate mlineindex {}: {}".format(
                        mlineindex, candidate
                    )
                )
                self.webrtcbin.emit("add-ice-candidate", mlineindex, candidate)
            elif line.startswith("m="):
                mlineindex += 1

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
