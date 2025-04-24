import asyncio
import logging

from janus_client import JanusSession
from janus_client.experiments.plugin_video_room_ffmpeg import JanusVideoRoomPlugin
import ffmpeg

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
logger = logging.getLogger()

room_id = 1234
publisher_id = 333
display_name = "qweqwe"

width = 640
height = 480
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


async def main():
    # Create session
    # session = JanusSession(
    #     base_url="wss://janusmy.josephgetmyip.com/janusbasews/janus",
    # )
    session = JanusSession(
        base_url="https://janusmy.josephgetmyip.com/janusbase/janus",
    )

    # Create plugin
    plugin_handle = JanusVideoRoomPlugin()

    # Attach to Janus session
    await plugin_handle.attach(session=session)
    logger.info("plugin created")

    await plugin_handle.join(room_id, publisher_id, display_name)
    logger.info("room joined")

    await plugin_handle.publish(ffmpeg_input=ffmpeg_input, width=width, height=height)
    logger.info("Let it stream for 60 seconds")
    await asyncio.sleep(60)
    logger.info("Stop streaming")
    await plugin_handle.unpublish()
    logger.info("Stream unpublished")

    # Destroy plugin
    await plugin_handle.destroy()


if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        pass
