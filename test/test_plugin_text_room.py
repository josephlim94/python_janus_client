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


def async_test_auto(coro):
    @async_test
    async def wrapper(*args, **kwargs):
        await args[0].asyncSetUp()

        try:
            return await coro(*args, **kwargs)
        finally:
            await args[0].asyncTearDown()

    return wrapper


class BaseTestClass:
    class TestClass(unittest.TestCase):
        server_url: str

        async def asyncSetUp(self) -> None:
            self.transport = JanusTransport.create_transport(
                base_url=self.server_url, api_secret="janusrocks"
            )
            await self.transport.connect()

            self.session = JanusSession(transport=self.transport)

        async def asyncTearDown(self) -> None:
            await self.session.destroy()

            await self.transport.disconnect()
            # https://docs.aiohttp.org/en/stable/client_advanced.html#graceful-shutdown
            # Working around to avoid "Exception ignored in: <function _ProactorBasePipeTransport.__del__ at 0x0000024A04C60280>"
            await asyncio.sleep(0.250)

        @async_test
        async def test_list_room(self):
            """Test "list" API."""
            await self.asyncSetUp()

            plugin = JanusTextRoomPlugin()

            await plugin.attach(session=self.session)

            room_list = await plugin.list_rooms()
            # There will be 1 static room configured in Janus default config
            self.assertTrue(
                len(list(filter(lambda room: room["room"] == 1234, room_list))) > 0
            )

            await self.asyncTearDown()

        @async_test
        async def test_join_room(self):
            """Test "join" API."""
            await self.asyncSetUp()

            plugin = JanusTextRoomPlugin()

            await plugin.attach(session=self.session)

            # There will be 1 static room configured in Janus default config
            is_success = await plugin.join_room(room=1234, username="test_username")
            self.assertTrue(is_success)

            await self.asyncTearDown()

        @async_test
        async def test_list_participants(self):
            """Test "join" API."""
            await self.asyncSetUp()

            plugin = JanusTextRoomPlugin()

            await plugin.attach(session=self.session)

            room_id = 1234

            # There will be 1 static room configured in Janus default config
            is_success = await plugin.join_room(room=room_id, username="test_username")
            self.assertTrue(is_success)

            participant_list = await plugin.list_participants(room=room_id)
            self.assertTrue(
                len(
                    list(
                        filter(
                            lambda participant: participant["username"]
                            == "test_username",
                            participant_list,
                        )
                    )
                )
                > 0
            )

            await self.asyncTearDown()

        @async_test_auto
        async def test_message(self):
            """Test "message" API."""
            plugin = JanusTextRoomPlugin()

            await plugin.attach(session=self.session)

            room_id = 1234

            # There will be 1 static room configured in Janus default config
            is_success = await plugin.join_room(room=room_id, username="test_username")
            self.assertTrue(is_success)

            message_response = await plugin.message_room(
                room=room_id, text="test message"
            )
            self.assertTrue(message_response)

        @async_test_auto
        async def test_setup(self):
            """Test "setup" API."""
            plugin = JanusTextRoomPlugin()

            await plugin.attach(session=self.session)

            await plugin.setup()


class TestTransportHttps(BaseTestClass.TestClass):
    server_url = "https://janusmy.josephgetmyip.com/janusbase/janus"


class TestTransportWebsocketSecure(BaseTestClass.TestClass):
    server_url = "wss://janusmy.josephgetmyip.com/janusbasews/janus"
