
import ssl
import asyncio
import pathlib
from concurrent.futures import TimeoutError

# from core import JanusClient
# from session import JanusSession
from video_room_plugin import JanusVideoRoomPlugin
from janus_client import JanusClient, JanusSession

import gi
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gst

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
localhost_pem = pathlib.Path(__file__).with_name("lt_limmengkiat_name_my.crt")
ssl_context.load_verify_locations(localhost_pem)
# ssl_context.check_hostname = False
# ssl_context.verify_mode = ssl.CERT_NONE

async def publish_some_video(session):
    # Create plugin
    plugin_handle = await session.create_plugin_handle(JanusVideoRoomPlugin)

    await plugin_handle.join(1234, 333, "qweqwe")
    await plugin_handle.publish()
    print("Let it stream for 60 seconds")
    await asyncio.sleep(60)
    print("Stop streaming")
    await plugin_handle.unpublish()
    print("Stream unpublished")

    # Destroy plugin
    await plugin_handle.destroy()

async def subscribe_to_a_feed(session):
    # Create plugin
    plugin_handle = await session.create_plugin_handle(JanusVideoRoomPlugin)

    participants = await plugin_handle.list_participants(1234)
    print(participants)
    if len(participants) > 0:
        # Publishers available
        participants_data_1 = participants[0]
        participant_id = participants_data_1["id"]

        await plugin_handle.subscribe(1234, participant_id)
        await asyncio.sleep(5)
        await plugin_handle.unsubscribe()
    # await plugin_handle.join(1234, 333, "qweqwe")
    # await asyncio.sleep(5)
    # await plugin_handle.unsubscribe()

    # Destroy plugin
    await plugin_handle.destroy()

async def main():
    client = JanusClient("wss://lt.limmengkiat.name.my:8989/", api_secret="janusrocks")
    await client.connect(ssl=ssl_context)
    # Create session
    session = await client.create_session(JanusSession)

    # await subscribe_to_a_feed(session)
    await publish_some_video(session)

    # Destroy session
    await session.destroy()
    # Destroy connection
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