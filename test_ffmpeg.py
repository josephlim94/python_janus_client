import asyncio

from janus_client import JanusClient, JanusSession
from janus_client.plugin_video_room_ffmpeg import JanusVideoRoomPlugin
from janus_client.media import MediaPlayer

pcs = set()


async def publish_some_video(session: JanusSession):
    # Create plugin
    plugin_handle: JanusVideoRoomPlugin = await session.create_plugin_handle(
        JanusVideoRoomPlugin
    )

    await plugin_handle.join(1234, 333, "qweqwe")
    await plugin_handle.publish()
    print("Let it stream for 60 seconds")
    await asyncio.sleep(60)
    print("Stop streaming")
    await plugin_handle.unpublish()
    print("Stream unpublished")

    # Destroy plugin
    await plugin_handle.destroy()


async def run(player, room_id):
    # Start connection
    client = JanusClient(
        uri="wss://janus.josephgetmyip.com/janusbasews/janus",
    )
    await client.connect()

    # Create session
    session = await client.create_session()

    # Create plugin
    # Attach message is sent, attaching this plugin to janus.
    plugin_handle: JanusVideoRoomPlugin = await session.create_plugin_handle(
        JanusVideoRoomPlugin
    )

    await plugin_handle.join(room_id, 333, "qweqwe")

    await plugin_handle.publish(player=player)
    print("Let it stream for 60 seconds")
    await asyncio.sleep(60)
    print("Stop streaming")
    await plugin_handle.unpublish()
    print("Stream unpublished")

    # Destroy plugin
    await plugin_handle.destroy()


if __name__ == "__main__":

    # create media source
    player = MediaPlayer(
        "C:\\Users\\Joseph\\Downloads\\De Kandar Demo.mp4",
        # format="h264",
        # options={"format_probesize": "32", "read_timeout": "1"},
    )

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(
            run(player=player, room_id=1234)
        )
    except KeyboardInterrupt:
        pass
