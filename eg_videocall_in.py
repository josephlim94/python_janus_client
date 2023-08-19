import asyncio
import logging

from janus_client import JanusSession, JanusVideoCallPlugin
from aiortc.contrib.media import MediaPlayer, MediaRecorder

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
logger = logging.getLogger()


async def on_incoming_call(plugin: JanusVideoCallPlugin, jsep: dict):
    # self.__player = MediaPlayer("./Into.the.Wild.2007.mp4")
    player = MediaPlayer(
        "http://download.tsi.telecom-paristech.fr/gpac/dataset/dash/uhd/mux_sources/hevcds_720p30_2M.mp4"
    )
    recorder = MediaRecorder("./videocall_record_in.mp4")
    pc = await plugin.create_pc(
        player=player,
        recorder=recorder,
        jsep=jsep,
    )

    await pc.setLocalDescription(await pc.createAnswer())
    jsep = {
        "sdp": pc.localDescription.sdp,
        "trickle": False,
        "type": pc.localDescription.type,
    }
    await plugin.accept(jsep=jsep, pc=pc, player=player, recorder=recorder)


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

    plugin_handle.on_incoming_call = on_incoming_call

    result = await plugin_handle.register(username=username_in)
    logger.info(result)

    # result = await plugin_handle.call(
    #     username=username, player=player, recorder=recorder
    # )
    # logger.info(result)

    if result:
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
