import asyncio
import logging
import os
from urllib.parse import urljoin

from dotenv import load_dotenv

load_dotenv()

# from janus_client.transport import JanusTransportHTTP
from janus_client import JanusSession, JanusEchoTestPlugin

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
logger = logging.getLogger()


async def main():
    # transport = JanusTransportHTTP(
    #     uri="https://janusmy.josephgetmyip.com/janusbase/janus"
    # )
    # session = JanusSession(base_url="wss://janusmy.josephgetmyip.com/janusbasews/janus")
    session = JanusSession(
        base_url=urljoin(
            os.getenv("JANUS_HTTP_URL", ""),
            os.getenv("JANUS_HTTP_BASE_PATH", ""),
        ),
        api_secret=os.getenv("JANUS_API_SECRET", ""),
    )

    plugin_handle = JanusEchoTestPlugin()

    await plugin_handle.attach(session=session)

    if os.path.exists("./asdasd.mp4"):
        os.remove("./asdasd.mp4")

    await plugin_handle.start(
        play_from="./Into.the.Wild.2007.mp4", record_to="./asdasd.mp4"
    )

    response = await session.transport.ping()
    logger.info(response)

    await asyncio.sleep(15)

    await plugin_handle.close_stream()

    await plugin_handle.destroy()

    await session.destroy()


if __name__ == "__main__":
    try:
        # asyncio.run(main=main())
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        pass
