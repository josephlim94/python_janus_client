import asyncio
import logging

# from janus_client.transport import JanusTransportHTTP
from janus_client import JanusSession, JanusEchoTestPlugin

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
logger = logging.getLogger()


async def test_task():
    # raise Exception("Exception in task")
    await asyncio.sleep(2)
    logger.info("done")


async def main():
    # transport = JanusTransportHTTP(
    #     uri="https://janusmy.josephgetmyip.com/janusbase/janus"
    # )
    session = JanusSession(base_url="wss://janusmy.josephgetmyip.com/janusbasews/janus")
    # session = JanusSession(base_url="https://janusmy.josephgetmyip.com/janusbase/janus")

    plugin_handle = JanusEchoTestPlugin()

    await plugin_handle.attach(session=session)

    await plugin_handle.start()

    response = await session.transport.ping()
    logger.info(response)

    await asyncio.sleep(10)

    await plugin_handle.destroy()

    await session.destroy()


async def main2():
    task = asyncio.create_task(test_task())
    await asyncio.sleep(3)
    raise task.exception()
    logger.info(exception)
    await task


if __name__ == "__main__":
    try:
        # asyncio.run(main=main())
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        pass
