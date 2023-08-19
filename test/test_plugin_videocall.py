import unittest
import logging
import asyncio

from janus_client import (
    JanusTransport,
    JanusSession,
    JanusVideoCallPlugin,
)
from test.util import async_test

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
logger = logging.getLogger()


class BaseTestClass:
    class TestClass(unittest.TestCase):
        server_url: str

        async def asyncSetUp(self) -> None:
            self.transport = JanusTransport.create_transport(base_url=self.server_url)
            await self.transport.connect()

        async def asyncTearDown(self) -> None:
            await self.transport.disconnect()
            # https://docs.aiohttp.org/en/stable/client_advanced.html#graceful-shutdown
            # Working around to avoid "Exception ignored in: <function _ProactorBasePipeTransport.__del__ at 0x0000024A04C60280>"
            await asyncio.sleep(0.250)

        @async_test
        async def test_sanity(self):
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)

            plugin = JanusVideoCallPlugin()

            await plugin.attach(session=session)

            await session.destroy()

            await self.asyncTearDown()

        @async_test
        async def test_list(self):
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)

            plugin_handle = JanusVideoCallPlugin()

            await plugin_handle.attach(session=session)

            list_username = await plugin_handle.list()
            self.assertTrue(type(list_username) is list)

            await plugin_handle.destroy()

            await session.destroy()

            await self.asyncTearDown()

        @async_test
        async def test_multiple_list(self):
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)

            plugin_handle = JanusVideoCallPlugin()

            await plugin_handle.attach(session=session)

            list_username_all = await asyncio.gather(
                plugin_handle.list(),
                plugin_handle.list(),
            )

            for result in list_username_all:
                self.assertTrue(type(result) is list)

            await plugin_handle.destroy()

            await session.destroy()

            await self.asyncTearDown()

        @async_test
        async def test_register_then_list(self):
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)

            plugin_handle = JanusVideoCallPlugin()

            await plugin_handle.attach(session=session)

            username = "test_user"

            register_result = await plugin_handle.register(username=username)
            self.assertTrue(register_result)

            list_username = await plugin_handle.list()
            self.assertTrue(username in list_username)

            await plugin_handle.destroy()

            await session.destroy()

            await self.asyncTearDown()


# class TestTransportHttps(BaseTestClass.TestClass):
#     server_url = "https://janusmy.josephgetmyip.com/janusbase/janus"


class TestTransportWebsocketSecure(BaseTestClass.TestClass):
    server_url = "wss://janusmy.josephgetmyip.com/janusbasews/janus"
