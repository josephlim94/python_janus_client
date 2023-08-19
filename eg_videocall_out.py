import asyncio
import logging

from janus_client import JanusSession, JanusVideoCallPlugin
from aiortc.contrib.media import MediaPlayer, MediaRecorder

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
logger = logging.getLogger()


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

    username = "testusernamein"
    username_out = "testusernameout"
    # player = MediaPlayer("./Into.the.Wild.2007.mp4")
    # player = MediaPlayer("http://download.tsi.telecom-paristech.fr/gpac/dataset/dash/uhd/mux_sources/hevcds_720p30_2M.mp4")
    player = MediaPlayer(
        "desktop",
        format="gdigrab",
        options={
            "video_size": "640x480",
            "framerate": "30",
            "offset_x": "20",
            "offset_y": "30",
        },
    )
    recorder = MediaRecorder("./videocall_record_out.mp4")

    result = await plugin_handle.register(username=username_out)
    logger.info(result)

    result = await plugin_handle.call(
        username=username, player=player, recorder=recorder
    )
    logger.info(result)

    await asyncio.sleep(30)

    result = await plugin_handle.hangup()
    logger.info(result)

    # Destroy plugin
    await plugin_handle.destroy()

    # Destroy session
    await session.destroy()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
