import unittest
import logging
import asyncio

from janus_client import JanusAdminMonitorClient
from test.util import async_test

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
logger = logging.getLogger()


class BaseTestClass:
    class TestClass(unittest.TestCase):
        server_url: str
        admin_secret: str

        async def asyncSetUp(self) -> None:
            self.admin_client = JanusAdminMonitorClient(
                base_url=self.server_url,
                admin_secret="janusoverlord",
            )
            await self.admin_client.connect()

        async def asyncTearDown(self) -> None:
            await self.admin_client.disconnect()
            # https://docs.aiohttp.org/en/stable/client_advanced.html#graceful-shutdown
            # Working around to avoid "Exception ignored in: <function _ProactorBasePipeTransport.__del__ at 0x0000024A04C60280>"
            await asyncio.sleep(0.250)

        @async_test
        async def test_sanity(self):
            await self.asyncSetUp()

            response = await self.admin_client.ping()
            self.assertEqual(response["janus"], "pong")

            await self.asyncTearDown()

        @async_test
        async def test_info(self):
            await self.asyncSetUp()

            response = await self.admin_client.info()
            self.assertEqual(response["janus"], "server_info")
            self.assertEqual(response["name"], "Janus WebRTC Server")

            await self.asyncTearDown()

        @async_test
        async def test_loops_info(self):
            await self.asyncSetUp()

            response = await self.admin_client.loops_info()
            self.assertListEqual(response, [])

            await self.asyncTearDown()

        @async_test
        async def test_get_settings(self):
            await self.asyncSetUp()

            response = await self.admin_client.get_settings()
            # Need to make sure this doesn't change on test server
            self.assertEqual(response["log_colors"], False)

            await self.asyncTearDown()

        @async_test
        async def test_set_session_timeout(self):
            await self.asyncSetUp()

            settings = await self.admin_client.get_settings()
            self.assertEqual(settings["log_colors"], False)

            response = await self.admin_client.set_session_timeout(
                settings["session_timeout"] + 1
            )
            self.assertEqual(response, settings["session_timeout"] + 1)

            response = await self.admin_client.set_session_timeout(
                settings["session_timeout"]
            )
            self.assertEqual(response, settings["session_timeout"])

            await self.asyncTearDown()

        @async_test
        async def test_set_log_level(self):
            await self.asyncSetUp()

            settings = await self.admin_client.get_settings()
            self.assertEqual(settings["log_colors"], False)

            response = await self.admin_client.set_log_level(
                settings["log_level"] + 1
            )
            self.assertEqual(response, settings["log_level"] + 1)

            response = await self.admin_client.set_log_level(
                settings["log_level"]
            )
            self.assertEqual(response, settings["log_level"])

            await self.asyncTearDown()

        @async_test
        async def test_set_log_timestamps(self):
            await self.asyncSetUp()

            settings = await self.admin_client.get_settings()
            self.assertEqual(settings["log_colors"], False)

            response = await self.admin_client.set_log_timestamps(
                not settings["log_timestamps"]
            )
            self.assertEqual(response, not settings["log_timestamps"])

            response = await self.admin_client.set_log_timestamps(
                settings["log_timestamps"]
            )
            self.assertEqual(response, settings["log_timestamps"])

            await self.asyncTearDown()


class TestTransportHttps(BaseTestClass.TestClass):
    server_url = "https://janusmy.josephgetmyip.com/janusadminbase/admin"


class TestTransportWebsocketSecure(BaseTestClass.TestClass):
    server_url = "wss://janusmy.josephgetmyip.com/janusadminbasews/admin"
