import asyncio
import logging

from janus_client import JanusSession, JanusVideoCallPlugin
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
    session = JanusSession(
        base_url="wss://janusmy.josephgetmyip.com/janusbasews/janus",
    )

    # Create plugin
    plugin_handle = JanusVideoCallPlugin()

    # Attach to Janus session
    await plugin_handle.attach(session=session)
    logger.info("plugin created")

    await plugin_handle.register("test")
    result = await plugin_handle.register("test")
    logger.info(result)

    list_result = await asyncio.gather(
        plugin_handle.list(),
        plugin_handle.list(),
    )
    # list_response = await plugin_handle.list()
    logger.info(list_result)

    # Destroy plugin
    await plugin_handle.destroy()

    # Destroy session
    await session.destroy()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
