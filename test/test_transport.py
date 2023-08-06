import unittest
import logging
import asyncio

from janus_client import JanusTransport

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
logger = logging.getLogger()


class BaseTestClass:
    class TestClass(unittest.IsolatedAsyncioTestCase):
        server_url: str

        async def asyncSetUp(self) -> None:
            self.transport = JanusTransport.create_transport(base_url=self.server_url)
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


# class TestTransportHttp(BaseTestClass.TestClass):
#     server_url = "http://janusmy.josephgetmyip.com/janusbase/janus"


class TestTransportHttps(BaseTestClass.TestClass):
    server_url = "https://janusmy.josephgetmyip.com/janusbase/janus"


# class TestTransportWebsocket(BaseTestClass.TestClass):
#     server_url = "ws://janusmy.josephgetmyip.com/janusbasews/janus"


class TestTransportWebsocketSecure(BaseTestClass.TestClass):
    server_url = "wss://janusmy.josephgetmyip.com/janusbasews/janus"
