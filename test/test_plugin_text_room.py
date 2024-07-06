import unittest
import logging
import asyncio
import os

from janus_client import (
    JanusTransport,
    JanusSession,
    JanusTextRoomPlugin,
)
from janus_client.message_transaction import is_subset
from test.util import async_test

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
logger = logging.getLogger()


class BaseTestClass:
    class TestClass(unittest.TestCase):
        server_url: str

        async def asyncSetUp(self) -> None:
            self.transport = JanusTransport.create_transport(
                base_url=self.server_url, api_secret="janusrocks"
            )
            await self.transport.connect()

        async def asyncTearDown(self) -> None:
            await self.transport.disconnect()
            # https://docs.aiohttp.org/en/stable/client_advanced.html#graceful-shutdown
            # Working around to avoid "Exception ignored in: <function _ProactorBasePipeTransport.__del__ at 0x0000024A04C60280>"
            await asyncio.sleep(0.250)

        @async_test
        async def test_list_room(self):
            """Test "list" API."""
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)

            plugin = JanusTextRoomPlugin()

            await plugin.attach(session=session)

            room_list = await plugin.list()
            # There will be 1 static room configured in Janus default config
            self.assertTrue(
                len(list(filter(lambda room: room["room"] == 1234, room_list))) > 0
            )

            await session.destroy()

            await self.asyncTearDown()

        @async_test
        async def test_join_room(self):
            """Test "join" API."""
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)

            plugin = JanusTextRoomPlugin()

            await plugin.attach(session=session)

            # There will be 1 static room configured in Janus default config
            is_success = await plugin.join_room(room=1234)
            self.assertTrue(is_success)

            await session.destroy()

            await self.asyncTearDown()


# class TestTransportHttps(BaseTestClass.TestClass):
#     server_url = "https://janusmy.josephgetmyip.com/janusbase/janus"


class TestTransportWebsocketSecure(BaseTestClass.TestClass):
    server_url = "wss://janusmy.josephgetmyip.com/janusbasews/janus"
