import unittest
import logging
import asyncio

from janus_client import (
    JanusTransport,
    JanusSession,
    JanusPlugin,
    PluginAttachFail,
    JanusEchoTestPlugin,
)

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

        async def test_plugin_create_fail(self):
            session = JanusSession(transport=self.transport)

            plugin = JanusPlugin()

            with self.assertRaises(PluginAttachFail):
                await plugin.attach(session=session)

            await session.destroy()

        async def test_plugin_echotest_create(self):
            session = JanusSession(transport=self.transport)

            plugin = JanusEchoTestPlugin()

            await plugin.attach(session=session)

            await plugin.destroy()

            await session.destroy()


# class TestTransportHttps(BaseTestClass.TestClass):
#     server_url = "https://janusmy.josephgetmyip.com/janusbase/janus"


class TestTransportWebsocketSecure(BaseTestClass.TestClass):
    server_url = "wss://janusmy.josephgetmyip.com/janusbasews/janus"
