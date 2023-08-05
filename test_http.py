import asyncio
import logging

# from janus_client.transport import JanusTransportHTTP
from janus_client import JanusSession

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
logger = logging.getLogger()


async def main():
    # transport = JanusTransportHTTP(
    #     uri="https://janusmy.josephgetmyip.com/janusbase/janus"
    # )
    session = JanusSession(uri="https://janusmy.josephgetmyip.com/janusbase/janus")

    response = await session.send({"janus": "keepalive"})
    logger.info(response)

    await session.destroy()

    # response = await transport.info()
    # logger.info(response)

    # response = await transport.send({"janus": "create"})
    # logger.info(response)

    # session_id = int(response["data"]["id"])

    # response = await transport.send({"janus": "keepalive"}, session_id=session_id)
    # logger.info(response)

    # response = await transport.send({"janus": "destroy"}, session_id=session_id)
    # logger.info(response)


if __name__ == "__main__":
    try:
        # asyncio.run(main=main())
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        pass
