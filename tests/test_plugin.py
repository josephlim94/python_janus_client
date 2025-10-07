import unittest
import logging
import asyncio
import os
from urllib.parse import urljoin

from janus_client import (
    JanusTransport,
    JanusSession,
    PluginAttachFail,
    JanusEchoTestPlugin,
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
        async def test_plugin_create_fail(self):
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)

            plugin = JanusEchoTestPlugin()

            # Give it a dummy plugin name
            plugin.name = "dummy_name"

            with self.assertRaises(PluginAttachFail):
                await plugin.attach(session=session)

            await session.destroy()

            await self.asyncTearDown()

        @async_test
        async def test_plugin_echotest_create(self):
            await self.asyncSetUp()
            logger.info("Start")
            print("ewq")

            session = JanusSession(transport=self.transport)

            plugin_handle = JanusEchoTestPlugin()

            await plugin_handle.attach(session=session)

            output_filename = "./asdasd.mp4"

            if os.path.exists(output_filename):
                os.remove(output_filename)

            # await plugin_handle.start(
            #     play_from="./Into.the.Wild.2007.mp4", record_to=output_filename
            # )
            await plugin_handle.start(
                play_from="http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
                record_to=output_filename,
            )

            await plugin_handle.wait_webrtcup()

            response = await session.transport.ping()
            self.assertEqual(response["janus"], "pong")

            await asyncio.sleep(15)

            await plugin_handle.close_stream()

            if not os.path.exists(output_filename):
                self.fail(f"Stream record file ({output_filename}) is not created.")

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
