import unittest
import logging
import asyncio

from janus_client import JanusTransport


server_url = "https://janusmy.josephgetmyip.com/janusbase/janus"

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
logger = logging.getLogger()


class TestClass(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.transport = JanusTransport.create_transport(base_url=server_url)
        await self.transport.connect()

    async def asyncTearDown(self) -> None:
        await self.transport.disconnect()
        # https://docs.aiohttp.org/en/stable/client_advanced.html#graceful-shutdown
        # Working around to avoid "Exception ignored in: <function _ProactorBasePipeTransport.__del__ at 0x0000024A04C60280>"
        await asyncio.sleep(0.250)

    async def test_sanity(self):
        response = await self.transport.send(
            {"janus": "ping"},
            response_handler=lambda res: res if res["janus"] == "pong" else None,
        )
        self.assertEqual(response["janus"], "pong")
