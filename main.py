
from __future__ import annotations
import ssl
import asyncio
import pathlib
from concurrent.futures import TimeoutError

from janus_client import JanusClient, JanusAdminMonitorClient
from janus_client.plugin_video_room import JanusVideoRoomPlugin
from typing import TYPE_CHECKING, Type
if TYPE_CHECKING:
    from janus_client import JanusSession

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

async def publish_some_video(session: JanusSession):
    # Create plugin
    plugin_handle: JanusVideoRoomPlugin = await session.create_plugin_handle(JanusVideoRoomPlugin)

    await plugin_handle.join(1234, 333, "qweqwe")
    await plugin_handle.publish()
    print("Let it stream for 60 seconds")
    await asyncio.sleep(60)
    print("Stop streaming")
    await plugin_handle.unpublish()
    print("Stream unpublished")

    # Destroy plugin
    await plugin_handle.destroy()

async def subscribe_to_a_feed(session: JanusSession):
    # Create plugin
    plugin_handle: JanusVideoRoomPlugin = await session.create_plugin_handle(JanusVideoRoomPlugin)

    participants = await plugin_handle.list_participants(1234)
    print(participants)
    if len(participants) > 0:
        # Publishers available
        participants_data_1 = participants[0]
        participant_id = participants_data_1["id"]

        await plugin_handle.subscribe(1234, participant_id)
        await asyncio.sleep(30)
        await plugin_handle.unsubscribe()
    # await plugin_handle.join(1234, 333, "qweqwe")
    # await asyncio.sleep(5)
    # await plugin_handle.unsubscribe()

    # Destroy plugin
    await plugin_handle.destroy()

# API secret is used when you're communicating with Janus as a server,
# such as when wrapping Janus requests with another server
api_secret = "janusrocks"
async def main():
    # Start connection
    client = JanusClient(uri="wss://lt.limmengkiat.name.my:8989/",
        api_secret=api_secret,
        token="111")
    await client.connect(ssl=ssl_context)
    adminClient = JanusAdminMonitorClient("wss://lt.limmengkiat.name.my:7989/", "janusoverlord")
    await adminClient.connect(ssl=ssl_context)

    # Authentication
    token = "ccc"
    # The following statements are not documented
    # It's fine to add a token when it already exists
    # The plugin access scope will be limited to the unified set of existing access scope
    #   and new access scope when adding the token again. Thus, it is better to be explicit
    #   for security purposes.
    await adminClient.add_token(token, ["janus.plugin.videoroom"])
    client.token = token

    # Create session
    session = await client.create_session()

    # await subscribe_to_a_feed(session)
    await publish_some_video(session)

    # Destroy session
    await session.destroy()

    # Delete token
    await adminClient.remove_token(client.token)
    client.token = None

    # Destroy connection
    await adminClient.disconnect()
    await client.disconnect()
    print("End of main")

async def main2():
    adminClient = JanusAdminMonitorClient("wss://lt.limmengkiat.name.my:7989/", "janusoverlord")
    await adminClient.connect(ssl=ssl_context)

    # print(await adminClient.info())
    # print(await adminClient.ping())
    print(await adminClient.list_tokens())

    token = "cccs"
    await adminClient.add_token(token, ['janus.plugin.voicemail', 'janus.plugin.audiobridge'])
    await adminClient.list_tokens()
    await adminClient.remove_token(token)

    # Destroy connection
    await adminClient.disconnect()
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