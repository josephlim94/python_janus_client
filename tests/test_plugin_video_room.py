import unittest
import logging
import asyncio
import os
from urllib.parse import urljoin

from aiortc.contrib.media import MediaRecorder

from janus_client import (
    JanusTransport,
    JanusSession,
    JanusVideoRoomPlugin,
    MediaPlayer,
)
from tests.util import async_test

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
        async def test_create_edit_destroy(self):
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)

            plugin = JanusVideoRoomPlugin()

            await plugin.attach(session=session)

            room_id = 123

            response = await plugin.destroy_room(room_id)
            self.assertFalse(response)

            response = await plugin.edit(room_id)
            self.assertFalse(response)

            response = await plugin.create_room(room_id)
            self.assertTrue(response)

            response = await plugin.edit(room_id)
            self.assertTrue(response)

            response = await plugin.destroy_room(room_id)
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

            response = await plugin.destroy_room(room_id)
            self.assertFalse(response)

            response = await plugin.create_room(room_id)
            self.assertTrue(response)

            response = await plugin.exists(room_id)
            self.assertTrue(response)

            response = await plugin.destroy_room(room_id)
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

            response = await plugin.create_room(room_id)
            self.assertTrue(response)

            response = await plugin.allowed(room_id)
            self.assertTrue(response)

            response = await plugin.destroy_room(room_id)
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

            response = await plugin.create_room(room_id)
            self.assertTrue(response)

            response = await plugin.kick(room_id=room_id, id=22222)
            self.assertFalse(response)

            response = await plugin.destroy_room(room_id)
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

            response = await plugin.create_room(room_id)
            self.assertTrue(response)

            response = await plugin.moderate(
                room_id=room_id, id=22222, mid="0", mute=True
            )
            self.assertFalse(response)

            response = await plugin.destroy_room(room_id)
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

            response = await plugin.create_room(room_id)
            self.assertTrue(response)

            room_list = await plugin.list_room()
            self.assertTrue(
                len(list(filter(lambda room: room["room"] == room_id, room_list))) > 0
            )

            response = await plugin.destroy_room(room_id)
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

            response = await plugin.create_room(room_id)
            self.assertTrue(response)

            room_list = await plugin.list_participants(room_id=room_id)
            self.assertListEqual(room_list, [])

            response = await plugin.destroy_room(room_id)
            self.assertTrue(response)

            await session.destroy()

            await self.asyncTearDown()

        @async_test
        async def test_join_and_leave(self):
            """Test "join" API."""
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)

            plugin = JanusVideoRoomPlugin()

            await plugin.attach(session=session)

            room_id = 123

            response = await plugin.create_room(room_id)
            self.assertTrue(response)

            response = await plugin.join(room_id=room_id)
            self.assertTrue(response)

            response = await plugin.leave()
            self.assertTrue(response)

            response = await plugin.destroy_room(room_id)
            self.assertTrue(response)

            await session.destroy()

            await self.asyncTearDown()

        @async_test
        async def test_publish_and_unpublish(self):
            """Test publish and then unpublish media."""

            await self.asyncSetUp()

            async with JanusSession(transport=self.transport) as session:
                plugin = JanusVideoRoomPlugin()

                await plugin.attach(session=session)

                room_id = 12345

                response = await plugin.destroy_room(room_id)
                self.assertFalse(response)

                response = await plugin.create_room(room_id)
                self.assertTrue(response)

                response = await plugin.join(
                    room_id=room_id, display_name="Test video room"
                )
                self.assertTrue(response)

                # player = MediaPlayer("./Into.the.Wild.2007.mp4")
                player = MediaPlayer(
                    "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
                )
                response = await plugin.publish(stream_track=player.stream_tracks)
                self.assertTrue(response)

                await asyncio.sleep(15)

                response = await plugin.unpublish()
                self.assertTrue(response)

                player.stop()

                response = await plugin.leave()
                self.assertTrue(response)

                response = await plugin.destroy_room(room_id)
                self.assertTrue(response)

                # Don't need to destroy if using context manager, but still good to do it
                await session.destroy()

            await self.asyncTearDown()

        @async_test
        async def test_publish_and_subscribe(self):
            """Test publish and then subscribe to the same media."""
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)

            plugin_publish = JanusVideoRoomPlugin()
            plugin_subscribe = JanusVideoRoomPlugin()

            await asyncio.gather(
                plugin_publish.attach(session=session),
                plugin_subscribe.attach(session=session),
            )

            # Janus demo uses room_id = 1234
            room_id = 12345

            response = await plugin_publish.destroy_room(room_id)
            self.assertFalse(response)

            response = await plugin_publish.create_room(room_id)
            self.assertTrue(response)

            response = await plugin_publish.join(
                room_id=room_id, display_name="Test video room publish"
            )
            self.assertTrue(response)

            # response = await plugin_subscribe.join(
            #     room_id=room_id, display_name="Test video room subscribe"
            # )
            # self.assertTrue(response)

            # player = MediaPlayer("./Into.the.Wild.2007.mp4")
            player = MediaPlayer(
                "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
            )
            response = await plugin_publish.publish(stream_track=player.stream_tracks)
            self.assertTrue(response)

            await asyncio.sleep(10)

            participants = await plugin_subscribe.list_participants(room_id=room_id)
            self.assertEqual(len(participants), 1)

            output_filename_out = "./video_room_record_out.mp4"
            if os.path.exists(output_filename_out):
                os.remove(output_filename_out)
            recorder = MediaRecorder(output_filename_out)

            async def on_track_created(track):
                logger.info("Track %s received" % track.kind)
                if track.kind == "video":
                    recorder.addTrack(track)
                if track.kind == "audio":
                    recorder.addTrack(track)

                await recorder.start()

            response = await plugin_subscribe.subscribe_and_start(
                room_id=room_id,
                on_track_created=on_track_created,
                stream={"feed": participants[0]["id"]},
            )
            self.assertTrue(response)

            await asyncio.sleep(30)

            response = await plugin_subscribe.unsubscribe()
            self.assertTrue(response)

            await recorder.stop()

            response = await plugin_publish.unpublish()
            self.assertTrue(response)

            player.stop()

            response = await plugin_publish.leave()
            self.assertTrue(response)

            response = await plugin_publish.destroy_room(room_id)
            self.assertTrue(response)

            await session.destroy()

            await self.asyncTearDown()


class TestTransportHttp(BaseTestClass.TestClass):
    server_url = urljoin(
        os.getenv("JANUS_HTTP_URL", ""),
        os.getenv("JANUS_HTTP_BASE_PATH", ""),
    )


class TestTransportWebsocket(BaseTestClass.TestClass):
    server_url = os.getenv("JANUS_WS_URL", "")
