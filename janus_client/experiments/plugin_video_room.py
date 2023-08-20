
from ..plugin_base import JanusPlugin
import asyncio
import logging
logger = logging.getLogger(__name__)

import gi
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gst
gi.require_version('GstWebRTC', '1.0')
from gi.repository import GstWebRTC
gi.require_version('GstSdp', '1.0')
from gi.repository import GstSdp

# Set to False to send H.264
DO_VP8 = True
# Set to False to disable RTX (lost packet retransmission)
DO_RTX = True
# Choose the video source:
VIDEO_SRC="videotestsrc pattern=ball"
# VIDEO_SRC = "v4l2src"

if DO_VP8:
    (encoder, payloader, rtp_encoding) = (
        "vp8enc target-bitrate=100000 overshoot=25 undershoot=100 deadline=33000 keyframe-max-dist=1", "rtpvp8pay picture-id-mode=2", "VP8")
else:
    (encoder, payloader, rtp_encoding) = ("x264enc",
                                          "rtph264pay aggregate-mode=zero-latency", "H264")

PIPELINE_DESC = '''
 webrtcbin name=sendrecv stun-server=stun://stun.l.google.com:19302
 {} ! video/x-raw,width=640,height=480 ! videoconvert ! queue !
 {} ! {} !  queue ! application/x-rtp,media=video,encoding-name={},payload=96 ! sendrecv.
'''.format(VIDEO_SRC, encoder, payloader, rtp_encoding)


class JanusVideoRoomPlugin(JanusPlugin):
    """Janus VideoRoom plugin instance

    Implements API to interact with VideoRoom plugin.
    """

    name = "janus.plugin.videoroom" #: Plugin name

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.joined_event = asyncio.Event()
        self.gst_webrtc_ready = asyncio.Event()
        self.loop = asyncio.get_running_loop()

        # Create a new pipeline, elements will be added to this.
        self.pipeline = Gst.Pipeline.new()

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

        await self.send({
            "janus": "message",
            "body": {
                "request": "join",
                "ptype": "publisher",
                "room": room_id,
                "id": publisher_id,
                "display": display_name,
            },
        })
        await self.joined_event.wait()

    async def publish(self) -> None:
        """Publish some hardcoded video stream to the handle

        Should already have joined a room before this. Then this will publish the
        hardcoded video stream to the handle.
        """

        # Initialize Gst WebRTC
        self.start_pipeline()
        await self.gst_webrtc_ready.wait()
        # Create offer
        promise = Gst.Promise.new()
        self.webrtcbin.emit('create-offer', None, promise)
        promise.wait()
        reply = promise.get_reply()
        offer = reply.get_value('offer')
        # Set local description
        promise = Gst.Promise.new()
        self.webrtcbin.emit('set-local-description', offer, promise)
        promise.interrupt()

        text = offer.sdp.as_text()
        logger.info('Sending offer and publishing:\n%s' % text)
        await self.send({
            "janus": "message",
            "body": {
                "request": "publish",
                "audio": True,
                "video": True,
            },
            "jsep": {
                'sdp': text,
                'type': 'offer',
                'trickle': True,
            }
        })
        await self.joined_event.wait()

    async def unpublish(self) -> None:
        """Stop publishing"""

        logger.info("Set pipeline to null")
        self.pipeline.set_state(Gst.State.NULL)
        logger.info("Set pipeline complete")
        await self.send({
            "janus": "message",
            "body": {
                "request": "unpublish",
            }
        })
        self.gst_webrtc_ready.clear()

    async def subscribe(self, room_id: int, feed_id: int) -> None:
        """Subscribe to a feed

        :param room_id: Room ID containing the feed. The same ID that
            you would use to join the room.
        :param feed_id: ID of the feed that you want to stream. Should be their publisher ID.
        """

        # Create webrtcbin element named app
        self.webrtcbin = Gst.ElementFactory.make("webrtcbin", "app")
        self.webrtcbin.connect('on-negotiation-needed',
                            self.on_negotiation_needed)
        self.webrtcbin.connect('on-ice-candidate',
                            self.send_ice_candidate_message)
        self.webrtcbin.connect('pad-added', self.on_incoming_stream)
        self.pipeline.add(self.webrtcbin)
        # trans = self.webrtcbin.emit('get-transceiver', 0)
        # if DO_RTX:
        #     trans.set_property('do-nack', True)
        self.pipeline.set_state(Gst.State.PLAYING)
        await self.send({
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
            }
        })
        await self.joined_event.wait()

    async def unsubscribe(self) -> None:
        """Unsubscribe from the feed"""

        self.pipeline.set_state(Gst.State.NULL)
        await self.send({
            "janus": "message",
            "body": {
                "request": "leave",
            }
        })
        self.joined_event.clear()
        self.gst_webrtc_ready.clear()

    async def start(self, answer=None) -> None:
        """Signal WebRTC start. I guess"""

        payload = {
            "janus": "message",
            "body": {
                "request": "start"
            }
        }
        if answer:
            payload["jsep"] = {
                'sdp': answer,
                'type': 'answer',
                'trickle': True,
            }
        await self.send(payload)

    async def pause(self) -> None:
        """Pause media streaming"""

        await self.send({
            "janus": "message",
            "body": {
                "request": "pause",
            }
        })

    async def list_participants(self, room_id: int) -> list:
        """Get participant list

        Get a list of publishers in the room, that are currently publishing.

        :param room_id: List participants in this room
        :return: A list containing the participants. Can be empty.
        """

        response = await self.send({
            "janus": "message",
            "body": {
                "request": "listparticipants",
                "room": room_id,
            }
        })
        return response["plugindata"]["data"]["participants"]

    def on_negotiation_needed(self, element):
        logger.info("on_negotiation_needed called")
        self.gst_webrtc_ready.set()
        # promise = Gst.Promise.new_with_change_func(self.on_offer_created, element, None)
        # element.emit('create-offer', None, promise)

    def send_ice_candidate_message(self, _, sdpMLineIndex, candidate):
        icemsg = {'candidate': candidate, 'sdpMLineIndex': sdpMLineIndex}
        logger.info (f"Sending ICE {icemsg}")
        # loop = asyncio.new_event_loop()
        future = asyncio.run_coroutine_threadsafe(
            self.trickle(sdpMLineIndex, candidate), self.loop)
        future.result()

    def on_incoming_decodebin_stream(self, _, pad):
        if not pad.has_current_caps():
            logger.info(pad, 'has no caps, ignoring')
            return

        caps = pad.get_current_caps()
        name = caps.to_string()
        if name.startswith('video'):
            q = Gst.ElementFactory.make('queue')
            conv = Gst.ElementFactory.make('videoconvert')
            sink = Gst.ElementFactory.make('autovideosink')
            self.pipeline.add(q)
            self.pipeline.add(conv)
            self.pipeline.add(sink)
            self.pipeline.sync_children_states()
            pad.link(q.get_static_pad('sink'))
            q.link(conv)
            conv.link(sink)
        elif name.startswith('audio'):
            q = Gst.ElementFactory.make('queue')
            conv = Gst.ElementFactory.make('audioconvert')
            resample = Gst.ElementFactory.make('audioresample')
            sink = Gst.ElementFactory.make('autoaudiosink')
            self.pipeline.add(q)
            self.pipeline.add(conv)
            self.pipeline.add(resample)
            self.pipeline.add(sink)
            self.pipeline.sync_children_states()
            pad.link(q.get_static_pad('sink'))
            q.link(conv)
            conv.link(resample)
            resample.link(sink)

    def on_incoming_stream(self, _, pad):
        if pad.direction != Gst.PadDirection.SRC:
            return

        decodebin = Gst.ElementFactory.make('decodebin')
        decodebin.connect('pad-added', self.on_incoming_decodebin_stream)
        self.pipeline.add(decodebin)
        decodebin.sync_state_with_parent()
        self.webrtcbin.link(decodebin)

    def start_pipeline(self):
        self.pipeline = Gst.parse_launch(PIPELINE_DESC)
        self.webrtcbin = self.pipeline.get_by_name('sendrecv')
        self.webrtcbin.connect('on-negotiation-needed',
                            self.on_negotiation_needed)
        self.webrtcbin.connect('on-ice-candidate',
                            self.send_ice_candidate_message)
        self.webrtcbin.connect('pad-added', self.on_incoming_stream)

        trans = self.webrtcbin.emit('get-transceiver', 0)
        if DO_RTX:
            trans.set_property('do-nack', True)
        self.pipeline.set_state(Gst.State.PLAYING)

    def extract_ice_from_sdp(self, sdp):
        mlineindex = -1
        for line in sdp.splitlines():
            if line.startswith("a=candidate"):
                candidate = line[2:]
                if mlineindex < 0:
                    logger.info("Received ice candidate in SDP before any m= line")
                    continue
                logger.info(
                    'Received remote ice-candidate mlineindex {}: {}'.format(mlineindex, candidate))
                self.webrtcbin.emit('add-ice-candidate', mlineindex, candidate)
            elif line.startswith("m="):
                mlineindex += 1

    async def handle_jsep(self, jsep):
        logger.info(jsep)
        if 'sdp' in jsep:
            sdp = jsep['sdp']
            if jsep['type'] == 'answer':
                logger.info('Received answer:\n%s' % sdp)
                _, sdpmsg = GstSdp.SDPMessage.new()
                GstSdp.sdp_message_parse_buffer(bytes(sdp.encode()), sdpmsg)

                answer = GstWebRTC.WebRTCSessionDescription.new(
                    GstWebRTC.WebRTCSDPType.ANSWER, sdpmsg)
                promise = Gst.Promise.new()
                self.webrtcbin.emit('set-remote-description', answer, promise)
                promise.interrupt()

                # Extract ICE candidates from the SDP to work around a GStreamer
                # limitation in (at least) 1.16.2 and below
                # This is tested to be not needed on 1.19.0.1
                # self.extract_ice_from_sdp(sdp)
            elif jsep['type'] == 'offer':
                logger.info('Received offer:\n%s' % sdp)
                _, sdpmsg = GstSdp.SDPMessage.new()
                GstSdp.sdp_message_parse_buffer(bytes(sdp.encode()), sdpmsg)

                offer = GstWebRTC.WebRTCSessionDescription.new(
                    GstWebRTC.WebRTCSDPType.OFFER, sdpmsg)
                promise = Gst.Promise.new()
                self.webrtcbin.emit('set-remote-description', offer, promise)
                promise.interrupt()

                # Extract ICE candidates from the SDP to work around a GStreamer
                # limitation in (at least) 1.16.2 and below
                self.extract_ice_from_sdp(sdp)

                # direction = GstWebRTC.WebRTCRTPTransceiverDirection.RECVONLY
                # caps = Gst.caps_from_string("application/x-rtp,media=video,encoding-name=VP8/9000,payload=96")
                # self.webrtcbin.emit('add-transceiver', direction, caps)

                # Create answer
                promise = Gst.Promise.new()
                self.webrtcbin.emit('create-answer', None, promise)
                promise.wait()
                reply = promise.get_reply()
                answer = reply.get_value('answer')
                # Set local description
                promise = Gst.Promise.new()
                self.webrtcbin.emit('set-local-description', answer, promise)
                promise.interrupt()

                answer_text = answer.sdp.as_text()
                await self.start(answer_text)
            else:
                raise Exception("Invalid JSEP")

        elif 'ice' in jsep:
            ice = jsep['ice']
            candidate = ice['candidate']
            sdpMLineIndex = ice['sdpMLineIndex']
            self.webrtcbin.emit('add-ice-candidate', sdpMLineIndex, candidate)
