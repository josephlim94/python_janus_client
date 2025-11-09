import unittest
import logging
import asyncio
import os
from urllib.parse import urljoin
import time
from typing import cast
import json

from aiortc.contrib.media import MediaPlayer, MediaRecorder
from aiortc import RTCConfiguration, RTCIceServer

from janus_client import (
    JanusTransport,
    JanusSession,
    JanusVideoCallPlugin,
    VideoCallEventType,
    VideoCallError,
)
from tests.util import async_test

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
logger = logging.getLogger()


class BaseTestClass:
    class TestClass(unittest.TestCase):
        server_url: str
        public_test_videos: dict

        @classmethod
        def setUpClass(cls):
            with open("./tests/public_test_videos.json", "r", encoding="utf-8") as file:
                cls.public_test_videos = json.load(file)

        def getVideoUrlByIndex(self, index: int):
            return self.public_test_videos["categories"][0]["videos"][index]["sources"][
                0
            ]

        async def asyncSetUp(self) -> None:
            self.transport = JanusTransport.create_transport(
                base_url=self.server_url, api_secret=os.getenv("JANUS_API_SECRET", "")
            )
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

            list_username = await plugin_handle.list_users()
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
                plugin_handle.list_users(),
                plugin_handle.list_users(),
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

            username = f"test_user_{int(time.time())}"

            register_result = await plugin_handle.register(username=username)
            self.assertTrue(register_result)
            self.assertEqual(plugin_handle.username, username)

            list_username = await plugin_handle.list_users()
            self.assertTrue(username in list_username)

            await plugin_handle.destroy()

            await session.destroy()

            await self.asyncTearDown()

        @async_test
        async def test_double_register_error(self):
            """Test that registering twice raises an error."""
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)
            plugin_handle = JanusVideoCallPlugin()

            try:
                await plugin_handle.attach(session=session)

                username = f"test_user_{int(time.time())}"
                await plugin_handle.register(username=username)

                # Try to register again - should raise error
                with self.assertRaises(VideoCallError) as context:
                    await plugin_handle.register(username=f"another_{username}")

                self.assertIn("Already registered", str(context.exception))

            finally:
                await plugin_handle.destroy()
                await session.destroy()
                await self.asyncTearDown()

        @async_test
        async def test_call_without_register_error(self):
            """Test that calling without registering raises an error."""
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)
            plugin_handle = JanusVideoCallPlugin()

            try:
                await plugin_handle.attach(session=session)

                # Try to call without registering - should raise error
                with self.assertRaises(VideoCallError) as context:
                    await plugin_handle.call(username="someone")

                self.assertIn("Must register", str(context.exception))

            finally:
                await plugin_handle.destroy()
                await session.destroy()
                await self.asyncTearDown()

        @async_test
        async def test_accept_without_register_error(self):
            """Test that accepting without registering raises an error."""
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)
            plugin_handle = JanusVideoCallPlugin()

            try:
                await plugin_handle.attach(session=session)

                # Try to accept without registering - should raise error
                jsep = {"type": "offer", "sdp": "fake_sdp"}
                with self.assertRaises(VideoCallError) as context:
                    await plugin_handle.accept(jsep=jsep)

                self.assertIn("Must register", str(context.exception))

            finally:
                await plugin_handle.destroy()
                await session.destroy()
                await self.asyncTearDown()

        @async_test
        async def test_accept_without_incoming_call_error(self):
            """Test that accepting without an incoming call raises an error."""
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)
            plugin_handle = JanusVideoCallPlugin()

            try:
                await plugin_handle.attach(session=session)

                username = f"test_user_{int(time.time())}"
                await plugin_handle.register(username=username)

                # Try to accept without incoming call - should raise error
                jsep = {"type": "offer", "sdp": "fake_sdp"}
                with self.assertRaises(VideoCallError) as context:
                    await plugin_handle.accept(jsep=jsep)

                self.assertIn("No incoming call", str(context.exception))

            finally:
                await plugin_handle.destroy()
                await session.destroy()
                await self.asyncTearDown()

        @async_test
        async def test_properties(self):
            """Test plugin properties."""
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)
            plugin_handle = JanusVideoCallPlugin()

            try:
                await plugin_handle.attach(session=session)

                # Initially no username and not in call
                self.assertIsNone(plugin_handle.username)
                self.assertFalse(plugin_handle.in_call)

                # After registration, username should be set
                username = f"test_user_{int(time.time())}"
                await plugin_handle.register(username=username)
                self.assertEqual(plugin_handle.username, username)
                self.assertFalse(plugin_handle.in_call)

            finally:
                await plugin_handle.destroy()
                await session.destroy()
                await self.asyncTearDown()

        @async_test
        async def test_set_media(self):
            """Test media configuration."""
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)
            plugin_handle = JanusVideoCallPlugin()

            try:
                await plugin_handle.attach(session=session)

                username = f"test_user_{int(time.time())}"
                await plugin_handle.register(username=username)

                # Test setting media parameters
                result = await plugin_handle.set_media(
                    audio=True,
                    video=True,
                    bitrate=128000,
                )
                self.assertTrue(result)

            finally:
                await plugin_handle.destroy()
                await session.destroy()
                await self.asyncTearDown()

        @async_test
        async def test_hangup(self):
            """Test hangup functionality."""
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)
            plugin_handle = JanusVideoCallPlugin()

            try:
                await plugin_handle.attach(session=session)

                username = f"test_user_{int(time.time())}"
                await plugin_handle.register(username=username)

                # Hangup should work even if not in a call
                result = await plugin_handle.hangup()
                self.assertTrue(result)
                self.assertFalse(plugin_handle.in_call)

            finally:
                await plugin_handle.destroy()
                await session.destroy()
                await self.asyncTearDown()

        @async_test
        async def test_video_call(self):
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)

            config = RTCConfiguration(
                iceServers=[
                    RTCIceServer(urls="stun:stun.l.google.com:19302"),
                ]
            )
            plugin_handle_in = JanusVideoCallPlugin(pc_config=config)
            plugin_handle_out = JanusVideoCallPlugin(pc_config=config)

            try:
                await plugin_handle_in.attach(session=session)
                await plugin_handle_out.attach(session=session)

                timestamp = str(int(time.time()))
                username_in = f"test_user_in_{timestamp}"
                username_out = f"test_user_out_{timestamp}"
                output_filename_in = "./videocall_record_in.mp4"
                output_filename_out = "./videocall_record_out.mp4"

                if os.path.exists(output_filename_in):
                    os.remove(output_filename_in)
                if os.path.exists(output_filename_out):
                    os.remove(output_filename_out)

                self.accept_call_task = None
                receive_call_event = asyncio.Event()

                async def on_incoming_call(data: dict):
                    player = MediaPlayer(self.getVideoUrlByIndex(0))
                    recorder = MediaRecorder(output_filename_in)

                    self.accept_call_task = asyncio.create_task(
                        plugin_handle_in.accept(
                            jsep=data["jsep"], player=player, recorder=recorder
                        )
                    )
                    receive_call_event.set()

                plugin_handle_in.on_event(
                    VideoCallEventType.INCOMINGCALL, on_incoming_call
                )

                register_result = await plugin_handle_in.register(username=username_in)
                self.assertTrue(register_result)
                register_result = await plugin_handle_out.register(
                    username=username_out
                )
                self.assertTrue(register_result)

                # player = MediaPlayer(
                #     "desktop",
                #     format="gdigrab",
                #     options={
                #         "video_size": "640x480",
                #         "framerate": "30",
                #         "offset_x": "20",
                #         "offset_y": "30",
                #     },
                # )
                player = MediaPlayer(self.getVideoUrlByIndex(4))
                recorder = MediaRecorder(output_filename_out)

                call_result = await plugin_handle_out.call(
                    username=username_in, player=player, recorder=recorder
                )
                self.assertTrue(call_result)

                await asyncio.wait_for(receive_call_event.wait(), timeout=15)
                self.assertIsNotNone(self.accept_call_task)
                accept_call_result = await cast(asyncio.Task, self.accept_call_task)
                self.assertTrue(accept_call_result)

                await asyncio.sleep(15)

                hangup_result = await plugin_handle_out.hangup()
                self.assertTrue(hangup_result)
                self.assertFalse(plugin_handle_out.in_call)

                hangup_result = await plugin_handle_in.hangup()
                self.assertTrue(hangup_result)
                self.assertFalse(plugin_handle_in.in_call)

                if not os.path.exists(output_filename_in):
                    self.fail(
                        f"Incoming call record file ({output_filename_in}) is not created."
                    )

                if not os.path.exists(output_filename_out):
                    self.fail(
                        f"Outgoing call record file ({output_filename_out}) is not created."
                    )

            finally:
                # TODO: Detaching both at the same time might hang. Should find out why.
                # await asyncio.gather(
                #     plugin_handle_in.destroy(), plugin_handle_out.destroy()
                # )
                await plugin_handle_in.destroy()
                await plugin_handle_out.destroy()

                await session.destroy()

                await self.asyncTearDown()

        @async_test
        async def test_error_response_handling(self):
            """Test error response handling."""
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)
            plugin_handle = JanusVideoCallPlugin()

            try:
                await plugin_handle.attach(session=session)

                # Try to call a non-existent user (with media to avoid aiortc error)
                username = f"test_user_{int(time.time())}"
                await plugin_handle.register(username=username)

                player = MediaPlayer(self.getVideoUrlByIndex(0))

                with self.assertRaises(VideoCallError):
                    await plugin_handle.call(
                        username="nonexistent_user_12345", player=player
                    )

            finally:
                await plugin_handle.destroy()
                await session.destroy()
                await self.asyncTearDown()

        @async_test
        async def test_destroy_cleanup(self):
            """Test that destroy properly cleans up resources."""
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)
            plugin_handle = JanusVideoCallPlugin()

            try:
                await plugin_handle.attach(session=session)

                username = f"test_user_{int(time.time())}"
                await plugin_handle.register(username=username)

                # Destroy should clean up state
                await plugin_handle.destroy()

                # After destroy, username should be cleared
                self.assertIsNone(plugin_handle.username)
                self.assertFalse(plugin_handle.in_call)

            finally:
                await session.destroy()
                await self.asyncTearDown()

        @async_test
        async def test_event_handler_exception_handling(self):
            """Test that exceptions in event handlers are caught and logged."""
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)
            plugin_handle = JanusVideoCallPlugin()

            try:
                await plugin_handle.attach(session=session)

                # Register a handler that raises an exception
                async def failing_handler(data):
                    raise RuntimeError("Test exception in handler")

                plugin_handle.on_event(VideoCallEventType.REGISTERED, failing_handler)

                # Register should still succeed even if handler fails
                username = f"test_user_{int(time.time())}"
                result = await plugin_handle.register(username=username)
                self.assertTrue(result)

                # Give time for event processing
                await asyncio.sleep(0.5)

            finally:
                await plugin_handle.destroy()
                await session.destroy()
                await self.asyncTearDown()


class TestTransportHttp(BaseTestClass.TestClass):
    server_url = urljoin(
        os.getenv("JANUS_HTTP_URL", ""),
        os.getenv("JANUS_HTTP_BASE_PATH", ""),
    )


class TestTransportWebsocket(BaseTestClass.TestClass):
    server_url = os.getenv("JANUS_WS_URL", "")
