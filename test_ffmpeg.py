import asyncio

from janus_client import JanusClient, JanusSession
from janus_client.plugin_video_room_ffmpeg import JanusVideoRoomPlugin
from janus_client.media import MediaPlayer
import ffmpeg

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


width = 640
height = 480


if __name__ == "__main__":
    # Specify the input part of ffmpeg
    ffmpeg_input = ffmpeg.input(
        "desktop",
        format="gdigrab",
        framerate=30,
        offset_x=20,
        offset_y=30,
        # s=f"{width}x{height}",
        video_size=[
            width,
            height,
        ],  # Using this video_size=[] or s="" is the same
        show_region=1,
    )

    # create media source
    player = MediaPlayer(
        ffmpeg_input,
        width,
        height,
    )

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run(player=player, room_id=1234))
    except KeyboardInterrupt:
        pass
