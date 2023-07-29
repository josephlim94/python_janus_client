import asyncio
import logging


from janus_client import JanusSession
from janus_client.plugin_video_room_ffmpeg import JanusVideoRoomPlugin
from janus_client.media import MediaPlayer
import ffmpeg

pcs = set()

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
logger = logging.getLogger()


async def run(player, room_id):
    # Create session
    session = JanusSession(
        uri="wss://janusmy.josephgetmyip.com/janusbasews/janus",
    )

    # Create plugin
    plugin_handle = JanusVideoRoomPlugin()

    # Attach to Janus session
    await plugin_handle.attach(session=session)

    # # Attach message is sent, attaching this plugin to janus.
    # plugin_handle = await session.create_plugin_handle(JanusVideoRoomPlugin)
    logger.info("plugin created")

    await plugin_handle.join(room_id, 333, "qweqwe")
    logger.info("room joined")

    await plugin_handle.publish(player=player)
    logger.info("Let it stream for 60 seconds")
    await asyncio.sleep(60)
    logger.info("Stop streaming")
    await plugin_handle.unpublish()
    logger.info("Stream unpublished")

    # Destroy plugin
    await plugin_handle.destroy()


width = 640
height = 480

# from janus_client.core import JanusMessage


# asd = {"qwe": 123}
# msg = JanusMessage(janus="ccc", **asd)
# logger.info(msg)
# logger.info(msg.model_dump())
# logger.info(msg.model_dump(exclude_none=True))
# logger.info(msg.model_dump_json(exclude_none=True))
# exit()

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

    try:
        asyncio.run(run(player=player, room_id=1234))
    except KeyboardInterrupt:
        pass
