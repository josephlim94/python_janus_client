import logging
from enum import Enum
from typing import List

from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    MediaStreamTrack,
)

from .plugin_base import JanusPlugin
from .message_transaction import is_subset

logger = logging.getLogger(__name__)


class AllowedAction(Enum):
    ENABLE = "enable"
    DISABLE = "disable"
    ADD = "add"
    REMOVE = "remove"


class JanusVideoRoomPlugin(JanusPlugin):
    """
    Janus VideoRoom plugin implementation

    Implements API to interact with VideoRoom plugin.

    Each plugin object is expected to have only 1 PeerConnection.

    Each VideoRoom plugin instance is expected to have one of the following
    three uses:
    - Administration
    - Publisher
    - Subscriber

    An instance meant for administration can be used as publisher or subscriber, but
    usually there isn't a reason to share. Just create another instance. On the
    other hand, a publisher instance cannot subscribe to a stream and vice versa.
    """

    name = "janus.plugin.videoroom"  #: Plugin name

    class State:
        STREAMING_OUT_MEDIA = "streaming_out_media"
        STREAMING_IN_MEDIA = "streaming_in_media"
        IDLE = "idle"

    __state: State

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.__state = self.State.IDLE

    # __on_record_start = lambda: None
    # __on_track_created = lambda: None
    async def __on_media_receive():
        """
        This method will be called when the PC receives media.
        It can be used to start a recorder.
        It may be called multiple times with no input.
        """
        raise NotImplementedError()

    async def __on_track_created(track: MediaStreamTrack):
        raise NotImplementedError()

    async def on_receive(self, response: dict):
        """Handle asynchronous messages"""

        janus_code = response["janus"]

        if janus_code == "media":
            if response["receiving"]:
                # It's ok to start multiple times, only the track that
                # has not been started will start
                if self.__state == self.State.STREAMING_IN_MEDIA:
                    self.__on_media_receive()
                elif self.__state == self.State.IDLE:
                    raise Exception("Media streaming when idle")

        if janus_code == "event":
            logger.info(f"Event response: {response}")
            # if "plugindata" in response:
            #     if response["plugindata"]["data"]["videoroom"] == "attached":
            #         # Subscriber attached
            #         self.joined_event.set()
            #     elif response["plugindata"]["data"]["videoroom"] == "joined":
            #         # Participant joined (joined as publisher but may not publish)
            #         self.joined_event.set()
        else:
            logger.info(f"Unimplemented response handle: {response}")

        # VideoRoom plugin doesn't send JSEP asynchronously

    async def send_wrapper(self, message: dict, matcher: dict, jsep: dict = {}) -> dict:
        def function_matcher(message: dict):
            return (
                is_subset(message, matcher)
                or is_subset(
                    message,
                    {
                        "janus": "success",
                        "plugindata": {
                            "plugin": self.name,
                            "data": {
                                "videoroom": "event",
                                "error_code": None,
                                "error": None,
                            },
                        },
                    },
                )
                or is_subset(
                    message,
                    {
                        "janus": "event",
                        "plugindata": {
                            "plugin": self.name,
                            "data": {
                                "videoroom": "event",
                                "error_code": None,
                                "error": None,
                            },
                        },
                    },
                )
                or is_subset(message, {"janus": "error", "error": {}})
            )

        full_message = message
        if jsep:
            full_message = {**message, "jsep": jsep}

        message_transaction = await self.send(
            message=full_message,
        )
        response = await message_transaction.get(matcher=function_matcher, timeout=15)
        await message_transaction.done()

        if is_subset(response, {"janus": "error", "error": {}}):
            raise Exception(f"Janus error: {response}")

        return response

    async def create_room(self, room_id: int, configuration: dict = {}) -> bool:
        """Create a room.

        Refer to documentation for description of parameters.
        https://janus.conf.meetecho.com/docs/videoroom.html
        """

        success_matcher = {
            "janus": "success",
            "plugindata": {"plugin": self.name, "data": {"videoroom": "created"}},
        }
        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": {
                    "request": "create",
                    "room": room_id,
                    **configuration,
                },
            },
            matcher=success_matcher,
        )

        return is_subset(response, success_matcher)

    async def destroy_room(
        self, room_id: int, secret: str = "", permanent: bool = False
    ) -> bool:
        """Destroy a room.

        All other participants in the room will also get the "destroyed" event.
        """

        success_matcher = {
            "janus": "success",
            "plugindata": {
                "plugin": self.name,
                "data": {"videoroom": "destroyed", "room": room_id},
            },
        }
        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": {
                    "request": "destroy",
                    "room": room_id,
                    "secret": secret,
                    "permanent": permanent,
                },
            },
            matcher=success_matcher,
        )

        return is_subset(response, success_matcher)

    async def edit(
        self,
        room_id: int,
        secret: str = "",
        new_description: str = "",
        new_secret: str = "",
        new_pin: str = "",
        new_is_private: bool = False,
        new_require_pvtid: bool = False,
        new_bitrate: int = None,
        new_fir_freq: int = None,
        new_publishers: int = 3,
        new_lock_record: bool = False,
        new_rec_dir: str = None,
        permanent: bool = False,
    ) -> bool:
        """Edit a room."""

        success_matcher = {
            "janus": "success",
            "plugindata": {
                "plugin": self.name,
                "data": {"videoroom": "edited", "room": room_id},
            },
        }

        body = {
            "request": "edit",
            "room": room_id,
            "secret": secret,
            "new_description": new_description,
            "new_secret": new_secret,
            "new_pin": new_pin,
            "new_is_private": new_is_private,
            "new_require_pvtid": new_require_pvtid,
            "new_publishers": new_publishers,
            "new_lock_record": new_lock_record,
            "permanent": permanent,
        }
        if new_bitrate:
            body["new_bitrate"] = new_bitrate
        if new_fir_freq:
            body["new_fir_freq"] = new_fir_freq
        if new_rec_dir:
            body["new_rec_dir"] = new_rec_dir

        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": body,
            },
            matcher=success_matcher,
        )

        return is_subset(response, success_matcher)

    async def exists(self, room_id: int) -> bool:
        """Check if a room exists."""

        success_matcher = {
            "janus": "success",
            "plugindata": {
                "plugin": self.name,
                "data": {"videoroom": "success", "room": room_id, "exists": None},
            },
        }
        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": {
                    "request": "exists",
                    "room": room_id,
                },
            },
            matcher=success_matcher,
        )

        return (
            is_subset(response, success_matcher)
            and response["plugindata"]["data"]["exists"]
        )

    async def allowed(
        self,
        room_id: int,
        secret: str = "",
        action: AllowedAction = AllowedAction.ENABLE,
        allowed: List[str] = [],
    ) -> bool:
        """Configure ACL of a room."""

        success_matcher = {
            "janus": "success",
            "plugindata": {
                "plugin": self.name,
                "data": {"videoroom": "success", "room": room_id, "allowed": None},
            },
        }
        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": {
                    "request": "allowed",
                    "room": room_id,
                    "secret": secret,
                    "action": action.value,
                    "allowed": allowed,
                },
            },
            matcher=success_matcher,
        )

        return is_subset(response, success_matcher)

    async def kick(
        self,
        room_id: int,
        id: str,
        secret: str = "",
    ) -> bool:
        """Kick a participant by ID.

        Only works for room administrators (i.e. you created the room).
        """

        success_matcher = {
            "janus": "success",
            "plugindata": {
                "plugin": self.name,
                "data": {"videoroom": "success"},
            },
        }
        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": {
                    "request": "kick",
                    "room": room_id,
                    "secret": secret,
                    "id": id,
                },
            },
            matcher=success_matcher,
        )

        return is_subset(response, success_matcher)

    async def moderate(
        self,
        room_id: int,
        id: str,
        mid: str,
        mute: bool,
        secret: str = "",
    ) -> bool:
        """Moderate a participant by ID.

        Only works for room administrators (i.e. you created the room).
        """

        success_matcher = {
            "janus": "success",
            "plugindata": {
                "plugin": self.name,
                "data": {"videoroom": "success"},
            },
        }
        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": {
                    "request": "moderate",
                    "room": room_id,
                    "secret": secret,
                    "id": id,
                    "mid": mid,
                    "mute": mute,
                },
            },
            matcher=success_matcher,
        )

        return is_subset(response, success_matcher)

    async def list_room(self) -> List[dict]:
        """List all rooms created.

        If admin_key is included, then private rooms will be listed as well.
        TODO: Find out how to include admin_key.
        """

        success_matcher = {
            "janus": "success",
            "plugindata": {
                "plugin": self.name,
                "data": {"videoroom": "success", "list": None},
            },
        }
        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": {
                    "request": "list",
                },
            },
            matcher=success_matcher,
        )

        if is_subset(response, success_matcher):
            return response["plugindata"]["data"]["list"]
        else:
            raise Exception(f"Fail to list rooms: {response}")

    async def list_participants(self, room_id: int) -> list:
        """Get participant list in a room

        Get a list of publishers in the room, that are currently publishing.

        :param room_id: List participants in this room
        :return: A list containing the participants. Can be empty.
        """

        success_matcher = {
            "janus": "success",
            "plugindata": {
                "plugin": self.name,
                "data": {
                    "videoroom": "participants",
                    "room": room_id,
                    "participants": None,
                },
            },
        }
        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": {
                    "request": "listparticipants",
                    "room": room_id,
                },
            },
            matcher=success_matcher,
        )

        if is_subset(response, success_matcher):
            return response["plugindata"]["data"]["participants"]
        else:
            raise Exception(f"Fail to list participants: {response}")

    async def join(
        self,
        room_id: int,
        publisher_id: int = None,
        display_name: str = "",
        token: str = None,
    ) -> bool:
        """Join a room

        A handle can join a room and then do nothing, but this should be called before publishing.
        There is an API to configure and publish at the same time, but it's not implemented yet.

        :param room_id: unique ID of the room to join.
        :param publisher_id: unique ID to register for the publisher; optional, will be chosen by the plugin if missing.
        :param display_name: display name for the publisher; optional.
        :param token: invitation token, in case the room has an ACL; optional.

        :return: True if room is created.
        """

        body = {
            "request": "join",
            "ptype": "publisher",
            "room": room_id,
            "display": display_name,
        }
        if publisher_id:
            body["publisher_id"] = publisher_id
        if token:
            body["token"] = token
        success_matcher = {
            "janus": "event",
            "plugindata": {
                "plugin": self.name,
                "data": {"videoroom": "joined", "room": room_id},
            },
        }

        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": body,
            },
            matcher=success_matcher,
        )

        return is_subset(response, success_matcher)

    async def leave(self) -> bool:
        """Leave the room. Will unpublish if publishing.

        :return: True if successfully leave.
        """

        success_matcher = {
            "janus": "event",
            "plugindata": {
                "plugin": self.name,
                "data": {"videoroom": "event", "leaving": "ok"},
            },
        }
        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": {
                    "request": "leave",
                },
            },
            matcher=success_matcher,
        )

        await self._pc.close()

        return is_subset(response, success_matcher)

    async def create_pc(
        self,
        stream_track: List[MediaStreamTrack] = [],
        jsep: dict = {},
    ) -> RTCPeerConnection:
        pc = RTCPeerConnection()

        for track in stream_track:
            pc.addTrack(track=track)

        # Must configure on track event before setRemoteDescription
        pc.on("track")(self.__on_track_created)
        # if recorder:

        #     @pc.on("track")
        #     async def on_track(track: MediaStreamTrack):
        #         logger.info("Track %s received" % track.kind)
        #         if track.kind == "video":
        #             recorder.addTrack(track)
        #         if track.kind == "audio":
        #             recorder.addTrack(track)

        #         await recorder.start()

        if jsep:
            await pc.setRemoteDescription(
                RTCSessionDescription(sdp=jsep["sdp"], type=jsep["type"])
            )

        return pc

    async def publish(
        self,
        stream_track: List[MediaStreamTrack],
        configuration: dict = {},
    ) -> None:
        """Publish video stream to the room

        Should already have joined a room before this.
        """

        self._pc = await self.create_pc(stream_track=stream_track)

        # send offer
        await self._pc.setLocalDescription(await self._pc.createOffer())
        self.__state = self.State.STREAMING_OUT_MEDIA

        body = {
            "request": "publish",
            # "audiocodec" : "<audio codec to prefer among the negotiated ones; optional>",
            # "videocodec" : "<video codec to prefer among the negotiated ones; optional>",
            # "bitrate" : <bitrate cap to return via REMB; optional, overrides the global room value if present>,
            # "record" : <true|false, whether this publisher should be recorded or not; optional>,
            # "filename" : "<if recording, the base path/file to use for the recording files; optional>",
            # "display" : "<display name to use in the room; optional>",
            # "audio_level_average" : "<if provided, overrided the room audio_level_average for this user; optional>",
            # "audio_active_packets" : "<if provided, overrided the room audio_active_packets for this user; optional>",
            # "descriptions" : [      // Optional
            #         {
            #                 "mid" : "<unique mid of a stream being published>",
            #                 "description" : "<text description of the stream (e.g., My front webcam)>"
            #         },
            #         // Other descriptions, if any
            # ]}
            **configuration,
        }

        success_matcher = {
            "janus": "event",
            "plugindata": {
                "plugin": self.name,
                "data": {"videoroom": "event", "configured": "ok"},
            },
        }
        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": body,
            },
            matcher=success_matcher,
            jsep=await self.create_jsep(pc=self._pc),
        )

        if is_subset(response, success_matcher):
            await self.on_receive_jsep(jsep=response["jsep"])

            return True
        else:
            return False

    async def unpublish(self) -> bool:
        """Stop publishing.

        :return: True if successfully unpublished.
        """

        self.__state = self.State.IDLE

        success_matcher = {
            "janus": "event",
            "plugindata": {
                "plugin": self.name,
                "data": {"videoroom": "event", "unpublished": "ok"},
            },
        }
        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": {
                    "request": "unpublish",
                },
            },
            matcher=success_matcher,
        )

        await self._pc.close()

        return is_subset(response, success_matcher)

    # TODO: Implement "configure", 'joinandconfigure", "rtp_forward", "stop_rtp_forward", "listforwarders", "enable_recording"

    async def subscribe_and_start(
        self,
        room_id: int,
        on_track_created,
        stream: dict,
        use_msid: bool = False,
        autoupdate: bool = True,
        private_id: int = None,
        # streams: List = [],
    ) -> bool:
        """Subscribe to a feed. Only supporting subscribe to 1 stream.

        :param room_id: Room ID containing the feed. The same ID that
            you would use to join the room.
        :param on_track_created: A callback function that will be called when AIORTC PC creates
            a media track
        :param stream: Configuration of the stream to subscribe to. Minimum should have
            a feed ID.
        :param use_msid: whether subscriptions should include an msid that references the publisher; false by default.
        :param autoupdate: whether a new SDP offer is sent automatically when a subscribed publisher leaves; true by default.
        :param private_id: unique ID of the publisher that originated this request; optional, unless mandated by the room configuration.
        """

        self.__state = self.State.STREAMING_IN_MEDIA

        body = {
            "request": "join",
            "ptype": "subscriber",
            "room": room_id,
            "use_msid": use_msid,
            "autoupdate": autoupdate,
            "streams": [stream],
        }
        if private_id:
            body["private_id"] = private_id

        success_matcher = {
            "janus": "event",
            "plugindata": {
                "plugin": self.name,
                "data": {"videoroom": "attached", "room": room_id, "streams": []},
            },
        }

        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": body,
            },
            matcher=success_matcher,
        )

        if not is_subset(response, success_matcher):
            raise Exception("Fail to subscribe.")

        # Successfully attached. Create PeerConnection then start.
        self.__on_track_created = on_track_created
        self._pc = await self.create_pc(
            jsep=response["jsep"],
        )
        await self._pc.setLocalDescription(await self._pc.createAnswer())

        return await self.start(
            jsep=await self.create_jsep(self._pc),
        )

    async def unsubscribe(self) -> None:
        """Unsubscribe from the feed"""

        self.__state = self.State.IDLE

        success_matcher = {
            "janus": "event",
            "plugindata": {
                "plugin": self.name,
                "data": {
                    "videoroom": "event",
                    "left": "ok",
                },
            },
        }

        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": {"request": "leave"},
            },
            matcher=success_matcher,
        )

        await self._pc.close()

        return is_subset(response, success_matcher)

    async def start(self, jsep: dict = None) -> bool:
        """Signal WebRTC start."""

        success_matcher = {
            "janus": "event",
            "plugindata": {
                "plugin": self.name,
                "data": {"videoroom": "event", "started": "ok"},
            },
        }

        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": {"request": "start"},
            },
            matcher=success_matcher,
            jsep=jsep,
        )

        return is_subset(response, success_matcher)

    async def pause(self) -> None:
        """Pause media streaming"""

        message_transaction = await self.send(
            {
                "janus": "message",
                "body": {
                    "request": "pause",
                },
            }
        )
        await message_transaction.get()
        await message_transaction.done()

    # async def handle_jsep(self, jsep):
    #     logger.info(jsep)
    #     if "sdp" in jsep:
    #         sdp = jsep["sdp"]
    #         if jsep["type"] == "answer":
    #             logger.info(f"Received answer:\n{sdp}")

    #             # apply answer
    #             await self.pc.setRemoteDescription(
    #                 RTCSessionDescription(sdp=jsep["sdp"], type=jsep["type"])
    #             )
    #         elif jsep["type"] == "offer":
    #             pass
    #         else:
    #             raise Exception("Invalid JSEP")

    #     elif "ice" in jsep:
    #         ice = jsep["ice"]
    #         candidate = ice["candidate"]
    #         sdpMLineIndex = ice["sdpMLineIndex"]
    #         self.webrtcbin.emit("add-ice-candidate", sdpMLineIndex, candidate)
