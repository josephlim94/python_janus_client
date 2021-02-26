
import ssl
import asyncio
import pathlib
from concurrent.futures import TimeoutError

from core import JanusClient
from session import JanusSession
from video_room_plugin import JanusVideoRoomPlugin

import gi
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gst
gi.require_version('GstWebRTC', '1.0')
from gi.repository import GstWebRTC
gi.require_version('GstSdp', '1.0')
from gi.repository import GstSdp

PIPELINE_DESC = '''
webrtcbin name=sendrecv bundle-policy=max-bundle
 autovideosrc ! videoconvert ! queue ! vp8enc deadline=1 ! rtpvp8pay !
 queue ! application/x-rtp,media=video,encoding-name=VP8,payload=97 ! sendrecv.
'''

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
localhost_pem = pathlib.Path(__file__).with_name("lt_limmengkiat_name_my.crt")
ssl_context.load_verify_locations(localhost_pem)
# ssl_context.check_hostname = False
# ssl_context.verify_mode = ssl.CERT_NONE

class WebRTCSubscriber:
    def __init__(self, client, session_id, handle_id):
        # self.id_ = id_
        self.pipe = None
        self.webrtc = None
        # self.peer_id = peer_id
        self.client = client
        self.session_id = session_id
        self.handle_id = handle_id
        self.started = False

    async def subscribe(self, feed_id):
        await self.client.send({
            "janus": "message",
            "session_id": self.session_id,
            "handle_id": self.handle_id,
            "body": {
                "request": "join",
                "ptype" : "subscriber",
                "room": 1234,
                "feed": feed_id,
                # "close_pc": True,
                # "audio": True,
                # "video": True,
                # "data": True,
                # "offer_audio": True,
                # "offer_video": True,
                # "offer_data": True,
                # "ack": True,
            }
        }, ack=True)

    async def unsubscribe(self):
        await self.client.send({
            "janus": "message",
            "session_id": self.session_id,
            "handle_id": self.handle_id,
            "body": {
                "request": "leave",
            }
        }, ack=True)
        # self.pipe.set_state(Gst.State.NULL)

    async def send_start(self, jsep):
        await self.client.send({
            "janus": "message",
            "session_id": self.session_id,
            "handle_id": self.handle_id,
            "body": {
                "request": "start",
            },
            "jsep": jsep
        }, ack=True)

    def send_sdp_offer(self, offer):
        text = offer.sdp.as_text()
        print ('Sending offer:\n%s' % text)
        # msg = json.dumps({'sdp': {'type': 'offer', 'sdp': text}})
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.send_start({'type': 'offer', 'sdp': text}))

    def on_offer_created(self, promise, _, __):
        promise.wait()
        reply = promise.get_reply()
        offer = reply.get_value('offer')
        promise = Gst.Promise.new()
        self.webrtc.emit('set-local-description', offer, promise)
        promise.interrupt()
        self.send_sdp_offer(offer)

    def on_negotiation_needed(self, element):
        promise = Gst.Promise.new_with_change_func(self.on_offer_created, element, None)
        element.emit('create-offer', None, promise)

    async def send_ice_candidate_client(self, candidate):
        await self.client.send({
            "janus": "trickle",
            "session_id": self.session_id,
            "handle_id": self.handle_id,
            "candidate": candidate,
        })

    def send_ice_candidate_message(self, _, mlineindex, candidate):
        # icemsg = json.dumps({'candidate': {'candidate': candidate, 'sdpMLineIndex': mlineindex}})
        print({'candidate': candidate, 'sdpMLineIndex': mlineindex})
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.send_ice_candidate_client({'candidate': candidate, 'sdpMLineIndex': mlineindex}))

    def on_incoming_decodebin_stream(self, _, pad):
        if not pad.has_current_caps():
            print (pad, 'has no caps, ignoring')
            return

        caps = pad.get_current_caps()
        name = caps.to_string()
        if name.startswith('video'):
            q = Gst.ElementFactory.make('queue')
            conv = Gst.ElementFactory.make('videoconvert')
            sink = Gst.ElementFactory.make('autovideosink')
            self.pipe.add(q)
            self.pipe.add(conv)
            self.pipe.add(sink)
            self.pipe.sync_children_states()
            pad.link(q.get_static_pad('sink'))
            q.link(conv)
            conv.link(sink)
        elif name.startswith('audio'):
            q = Gst.ElementFactory.make('queue')
            conv = Gst.ElementFactory.make('audioconvert')
            resample = Gst.ElementFactory.make('audioresample')
            sink = Gst.ElementFactory.make('autoaudiosink')
            self.pipe.add(q)
            self.pipe.add(conv)
            self.pipe.add(resample)
            self.pipe.add(sink)
            self.pipe.sync_children_states()
            pad.link(q.get_static_pad('sink'))
            q.link(conv)
            conv.link(resample)
            resample.link(sink)

    def on_incoming_stream(self, _, pad):
        if pad.direction != Gst.PadDirection.SRC:
            return

        decodebin = Gst.ElementFactory.make('decodebin')
        decodebin.connect('pad-added', self.on_incoming_decodebin_stream)
        self.pipe.add(decodebin)
        decodebin.sync_state_with_parent()
        self.webrtc.link(decodebin)

    def start_pipeline(self):
        self.pipe = Gst.parse_launch(PIPELINE_DESC)
        self.webrtc = self.pipe.get_by_name('sendrecv')
        self.webrtc.connect('on-negotiation-needed', self.on_negotiation_needed)
        self.webrtc.connect('on-ice-candidate', self.send_ice_candidate_message)
        self.webrtc.connect('pad-added', self.on_incoming_stream)
        self.pipe.set_state(Gst.State.PLAYING)

    async def handle_sdp(self, message):
        assert (self.webrtc)
        msg = json.loads(message)
        if 'sdp' in msg:
            sdp = msg['sdp']
            assert(sdp['type'] == 'answer')
            sdp = sdp['sdp']
            print ('Received answer:\n%s' % sdp)
            res, sdpmsg = GstSdp.SDPMessage.new()
            GstSdp.sdp_message_parse_buffer(bytes(sdp.encode()), sdpmsg)
            answer = GstWebRTC.WebRTCSessionDescription.new(GstWebRTC.WebRTCSDPType.ANSWER, sdpmsg)
            promise = Gst.Promise.new()
            self.webrtc.emit('set-remote-description', answer, promise)
            promise.interrupt()
        elif 'ice' in msg:
            ice = msg['ice']
            candidate = ice['candidate']
            sdpmlineindex = ice['sdpMLineIndex']
            self.webrtc.emit('add-ice-candidate', sdpmlineindex, candidate)

    async def loop(self):
        assert self.conn
        async for message in self.conn:
            if message == 'HELLO':
                await self.setup_call()
            elif message == 'SESSION_OK':
                self.start_pipeline()
            elif message.startswith('ERROR'):
                print (message)
                return 1
            else:
                await self.handle_sdp(message)
        return 0

async def subscribe_feed(client, session_id, handle_id):
    response_list_participants = await client.send({
        "janus": "message",
        "session_id": session_id,
        "handle_id": handle_id,
        "body": {
            "request": "listparticipants",
            "room": 1234,
        }
    })
    if len(response_list_participants["plugindata"]["data"]["participants"]) > 0:
        # Publishers available
        participants_data_1 = response_list_participants["plugindata"]["data"]["participants"][0]
        # print(publisher_data)
        participant_id = participants_data_1["id"]
        subscriber_client = WebRTCSubscriber(client, session_id, handle_id)
        await subscriber_client.subscribe(participant_id)
        # await client.send({
        #     "janus": "message",
        #     "session_id": session_id,
        #     "handle_id": handle_id,
        #     "body": {
        #         "request": "start",
        #     }
        # })
        # subscriber_client.start_pipeline()
        await asyncio.sleep(5)
        await subscriber_client.unsubscribe()
    # response_publish = await client.send({
    #     "janus": "message",
    #     "session_id": session_id,
    #     "handle_id": handle_id,
    #     "body": {
    #         "request": "join",
    #         "ptype" : "publisher",
    #         "room": 1234,
    #         "id": 333,
    #         "display": "qweasd"
    #     }
    # }, ack=True)
    # # if response_publish["janus"] == "ack":
    # #     print("Exiting because received ack from janus")
    # #     await asyncio.sleep(10)
    # #     exit(1)
    # if len(response_publish["plugindata"]["data"]["publishers"]) > 0:
    #     # Publishers available
    #     publishers_data_1 = response_publish["plugindata"]["data"]["publishers"][0]
    #     # print(publisher_data)
    #     publisher_id = publishers_data_1["id"]
    #     # Attach subscriber plugin
    #     response_plugin_subscriber = await client.send({
    #         "janus": "attach",
    #         "session_id": session_id,
    #         "plugin": "janus.plugin.videoroom",
    #         "opaque_id":"4444",
    #     })
    #     if response_plugin_subscriber["janus"] == "success":
    #         # Plugin attached
    #         subscriber_client = WebRTCSubscriber(client, session_id, response_plugin_subscriber["data"]["id"])
    #         response_publish = await client.send({
    #             "janus": "message",
    #             "session_id": session_id,
    #             "handle_id": response_plugin_subscriber["data"]["id"],
    #             "body": {
    #                 "request": "join",
    #                 "ptype" : "subscriber",
    #                 "room": 1234,
    #                 "feed": publisher_id,
    #                 "close_pc": True,
    #                 "audio": True,
    #                 "video": True,
    #                 "data": True,
    #                 "offer_audio": True,
    #                 "offer_video": True,
    #                 "offer_data": True,
    #                 "ack": False,
    #             }
    #         }, ack=True)
    #         # await subscriber_client.subscribe(publisher_id)
    #         # subscriber_client.start_pipeline()
    #         print("Waiting for SDP offer")
    #         await asyncio.sleep(30)
    #         # await subscriber_client.unsubscribe()
    #         # Destroy subscriber plugin
    #         response_leave = await client.send({
    #             "janus": "message",
    #             "session_id": session_id,
    #             "handle_id": response_plugin_subscriber["data"]["id"],
    #             "body": {
    #                 "request": "leave",
    #             }
    #         })
    #         response_detach = await client.send({
    #             "janus": "detach",
    #             "session_id": session_id,
    #             "handle_id": response_plugin_subscriber["data"]["id"],
    #         })
    #     # await client.send({
    #     #     "janus": "message",
    #     #     "session_id": session_id,
    #     #     "handle_id": handle_id,
    #     #     "body": {
    #     #         "request": "start",
    #     #     }
    #     # })
    # response_leave = await client.send({
    #     "janus": "message",
    #     "session_id": session_id,
    #     "handle_id": handle_id,
    #     "body": {
    #         "request": "leave",
    #     }
    # })

async def subscribe_feed_2(plugin_handle):
    response_list_participants = await plugin_handle.send({
        "janus": "message",
        "body": {
            "request": "listparticipants",
            "room": 1234,
        }
    })
    if len(response_list_participants["plugindata"]["data"]["participants"]) > 0:
        # Publishers available
        participants_data_1 = response_list_participants["plugindata"]["data"]["participants"][0]
        # print(publisher_data)
        participant_id = participants_data_1["id"]
        subscriber_client = WebRTCSubscriber(client, session_id, handle_id)
        await subscriber_client.subscribe(participant_id)
        # await client.send({
        #     "janus": "message",
        #     "session_id": session_id,
        #     "handle_id": handle_id,
        #     "body": {
        #         "request": "start",
        #     }
        # })
        # subscriber_client.start_pipeline()
        await asyncio.sleep(5)
        await subscriber_client.unsubscribe()

async def main():
    client = JanusClient("wss://lt.limmengkiat.name.my/janusws/")
    await client.connect(ssl=ssl_context)
    # Create session
    session = await client.create_session(JanusSession)
    plugin_handle = await session.create_plugin_handle(JanusVideoRoomPlugin)
    # await create_plugin(client, session.session_id)
    # await subscribe_feed_2(plugin_handle)
    await plugin_handle.destroy()
    await session.destroy()
    # response = await client.send({
    #     "janus": "create",
    # })
    # if response["janus"] == "success":
    #     # Session created
    #     # # Attach plugin
    #     # response_plugin = await client.send({
    #     #     "janus": "attach",
    #     #     "session_id": response["data"]["id"],
    #     #     "plugin": "janus.plugin.echotest",
    #     # })
    #     # print(response_plugin)
    #     # if response_plugin["janus"] == "success":
    #     #     # Plugin attached
    #     #     # Destroy plugin
    #     #     response_detach = await client.send({
    #     #         "janus": "detach",
    #     #         "session_id": response["data"]["id"],
    #     #         "handle_id": response_plugin["data"]["id"],
    #     #     })
    #     #     print(response_detach)
    #     # await asyncio.gather(create_plugin(client, response["data"]["id"]), create_plugin(client, response["data"]["id"]))
    #     await create_plugin(client, response["data"]["id"])
    #     # Destroy session
    #     reponse_destroy = await client.send({
    #         "janus": "destroy",
    #         "session_id": response["data"]["id"],
    #     })
    await client.disconnect()
    print("End of main")

def check_plugins():
    needed = ["opus", "vpx", "nice", "webrtc", "dtls", "srtp", "rtp",
              "rtpmanager", "videotestsrc", "audiotestsrc"]
    missing = list(filter(lambda p: Gst.Registry.get().find_plugin(p) is None, needed))
    if len(missing):
        print('Missing gstreamer plugins:', missing)
        return False
    return True

Gst.init(None)
check_plugins()
asyncio.run(main())