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

    # username = "testusername"
    username_in = "testusernamein"
    # player = MediaPlayer("./Into.the.Wild.2007.mp4")
    # recorder = MediaRecorder("./videocall_record.mp4")

    result = await plugin_handle.register(username=username_in)
    logger.info(result)

    # result = await plugin_handle.call(
    #     username=username, player=player, recorder=recorder
    # )
    # logger.info(result)

    await asyncio.sleep(60)

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
