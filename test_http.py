import asyncio
import logging

from janus_client.transport import JanusTransportHTTP

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
logger = logging.getLogger()


async def main():
    transport = JanusTransportHTTP(
        uri="https://janusmy.josephgetmyip.com/janusbase/janus"
    )

    response = await transport.info()
    logger.info(response)

    response = await transport.send({"janus": "create"})
    logger.info(response)

    response = await transport.send(
        {"janus": "destroy"}, session_id=int(response["data"]["id"])
    )
    logger.info(response)


if __name__ == "__main__":
    try:
        # asyncio.run(main=main())
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        pass
