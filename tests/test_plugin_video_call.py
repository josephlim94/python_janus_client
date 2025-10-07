import unittest
import logging
import asyncio
import os
from urllib.parse import urljoin

from aiortc.contrib.media import MediaPlayer, MediaRecorder

from janus_client import (
    JanusTransport,
    JanusSession,
    JanusVideoCallPlugin,
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

        @async_test
        async def test_video_call(self):
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)

            plugin_handle_in = JanusVideoCallPlugin()
            plugin_handle_out = JanusVideoCallPlugin()

            await plugin_handle_in.attach(session=session)
            await plugin_handle_out.attach(session=session)

            username_in = "test_user_in"
            username_out = "test_user_out"
            output_filename_in = "./videocall_record_in.mp4"
            output_filename_out = "./videocall_record_out.mp4"

            if os.path.exists(output_filename_in):
                os.remove(output_filename_in)
            if os.path.exists(output_filename_out):
                os.remove(output_filename_out)

            async def on_incoming_call(plugin: JanusVideoCallPlugin, jsep: dict):
                # player = MediaPlayer("./Into.the.Wild.2007.mp4")
                player = MediaPlayer(
                    "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
                )
                recorder = MediaRecorder(output_filename_in)
                pc = await plugin.create_pc(
                    player=player,
                    recorder=recorder,
                    jsep=jsep,
                )

                await pc.setLocalDescription(await pc.createAnswer())
                jsep = {
                    "sdp": pc.localDescription.sdp,
                    "trickle": False,
                    "type": pc.localDescription.type,
                }
                await plugin.accept(jsep=jsep, pc=pc, player=player, recorder=recorder)

            plugin_handle_in.on_incoming_call = on_incoming_call

            register_result = await plugin_handle_in.register(username=username_in)
            self.assertTrue(register_result)
            register_result = await plugin_handle_out.register(username=username_out)
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
            player = MediaPlayer(
                "http://download.tsi.telecom-paristech.fr/gpac/dataset/dash/uhd/mux_sources/hevcds_720p30_2M.mp4"
            )
            # player = MediaPlayer("../Into.the.Wild.2007.mp4")
            recorder = MediaRecorder(output_filename_out)

            call_result = await plugin_handle_out.call(
                username=username_in, player=player, recorder=recorder
            )
            self.assertTrue(call_result)

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

            await asyncio.gather(
                plugin_handle_in.destroy(), plugin_handle_out.destroy()
            )

            await session.destroy()

            await self.asyncTearDown()


class TestTransportHttp(BaseTestClass.TestClass):
    server_url = urljoin(
        os.getenv("JANUS_HTTP_URL", ""),
        os.getenv("JANUS_HTTP_BASE_PATH", ""),
    )


class TestTransportWebsocket(BaseTestClass.TestClass):
    server_url = os.getenv("JANUS_WS_URL", "")
