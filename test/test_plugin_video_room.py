import unittest
import logging
import asyncio

from janus_client import (
    JanusTransport,
    JanusSession,
    JanusVideoRoomPlugin,
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
        async def test_create_edit_destroy(self):
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)

            plugin = JanusVideoRoomPlugin()

            await plugin.attach(session=session)

            room_id = 123

            response = await plugin.destroy(room_id)
            self.assertFalse(response)

            response = await plugin.edit(room_id)
            self.assertFalse(response)

            response = await plugin.create(room_id)
            self.assertTrue(response)

            response = await plugin.edit(room_id)
            self.assertTrue(response)

            response = await plugin.destroy(room_id)
            self.assertTrue(response)

            await session.destroy()

            await self.asyncTearDown()

        @async_test
        async def test_exists(self):
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)

            plugin = JanusVideoRoomPlugin()

            await plugin.attach(session=session)

            room_id = 123

            response = await plugin.exists(room_id)
            self.assertFalse(response)

            response = await plugin.destroy(room_id)
            self.assertFalse(response)

            response = await plugin.create(room_id)
            self.assertTrue(response)

            response = await plugin.exists(room_id)
            self.assertTrue(response)

            response = await plugin.destroy(room_id)
            self.assertTrue(response)

            await session.destroy()

            await self.asyncTearDown()

        @async_test
        async def test_allowed(self):
            """Test "allowed" API.

            This is a dummy test to increase coverage.
            """
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)

            plugin = JanusVideoRoomPlugin()

            await plugin.attach(session=session)

            room_id = 123

            response = await plugin.create(room_id)
            self.assertTrue(response)

            response = await plugin.allowed(room_id)
            self.assertTrue(response)

            response = await plugin.destroy(room_id)
            self.assertTrue(response)

            await session.destroy()

            await self.asyncTearDown()

        @async_test
        async def test_kick(self):
            """Test "kick" API."""
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)

            plugin = JanusVideoRoomPlugin()

            await plugin.attach(session=session)

            room_id = 123

            response = await plugin.create(room_id)
            self.assertTrue(response)

            response = await plugin.kick(room_id=room_id, id=22222)
            self.assertFalse(response)

            response = await plugin.destroy(room_id)
            self.assertTrue(response)

            await session.destroy()

            await self.asyncTearDown()

        @async_test
        async def test_moderate(self):
            """Test "kick" API."""
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)

            plugin = JanusVideoRoomPlugin()

            await plugin.attach(session=session)

            room_id = 123

            response = await plugin.create(room_id)
            self.assertTrue(response)

            response = await plugin.moderate(
                room_id=room_id, id=22222, mid="0", mute=True
            )
            self.assertFalse(response)

            response = await plugin.destroy(room_id)
            self.assertTrue(response)

            await session.destroy()

            await self.asyncTearDown()

        @async_test
        async def test_list_room(self):
            """Test "list" API."""
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)

            plugin = JanusVideoRoomPlugin()

            await plugin.attach(session=session)

            room_id = 123

            response = await plugin.create(room_id)
            self.assertTrue(response)

            room_list = await plugin.list_room()
            self.assertTrue(
                len(list(filter(lambda room: room["room"] == room_id, room_list))) > 0
            )

            response = await plugin.destroy(room_id)
            self.assertTrue(response)

            await session.destroy()

            await self.asyncTearDown()

        @async_test
        async def test_list_participants(self):
            """Test "listparticipants" API."""
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)

            plugin = JanusVideoRoomPlugin()

            await plugin.attach(session=session)

            room_id = 123

            response = await plugin.create(room_id)
            self.assertTrue(response)

            room_list = await plugin.list_participants(room_id=room_id)
            self.assertListEqual(room_list, [])

            response = await plugin.destroy(room_id)
            self.assertTrue(response)

            await session.destroy()

            await self.asyncTearDown()

        @async_test
        async def test_join_and_leave(self):
            """Test "listparticipants" API."""
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)

            plugin = JanusVideoRoomPlugin()

            await plugin.attach(session=session)

            room_id = 123

            response = await plugin.create(room_id)
            self.assertTrue(response)

            response = await plugin.join(room_id=room_id)
            self.assertTrue(response)

            response = await plugin.leave()
            self.assertTrue(response)

            response = await plugin.destroy(room_id)
            self.assertTrue(response)

            await session.destroy()

            await self.asyncTearDown()


# class TestTransportHttps(BaseTestClass.TestClass):
#     server_url = "https://janusmy.josephgetmyip.com/janusbase/janus"


class TestTransportWebsocketSecure(BaseTestClass.TestClass):
    server_url = "wss://janusmy.josephgetmyip.com/janusbasews/janus"
