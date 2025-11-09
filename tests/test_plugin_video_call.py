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
)
from janus_client.plugin_video_call import VideoCallEventType
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

            username = "test_user"

            register_result = await plugin_handle.register(username=username)
            self.assertTrue(register_result)

            list_username = await plugin_handle.list_users()
            self.assertTrue(username in list_username)

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
                hangup_result = await plugin_handle_in.hangup()
                self.assertTrue(hangup_result)

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


class TestTransportHttp(BaseTestClass.TestClass):
    server_url = urljoin(
        os.getenv("JANUS_HTTP_URL", ""),
        os.getenv("JANUS_HTTP_BASE_PATH", ""),
    )


class TestTransportWebsocket(BaseTestClass.TestClass):
    server_url = os.getenv("JANUS_WS_URL", "")
