import unittest
import logging
import asyncio
import os
from urllib.parse import urljoin

from janus_client import JanusAdminMonitorClient
from tests.util import async_test

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
                admin_secret=self.admin_secret,
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

            response = await self.admin_client.set_log_level(settings["log_level"] + 1)
            self.assertEqual(response, settings["log_level"] + 1)

            response = await self.admin_client.set_log_level(settings["log_level"])
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

        @async_test
        async def test_set_log_colors(self):
            await self.asyncSetUp()

            settings = await self.admin_client.get_settings()
            self.assertEqual(settings["log_colors"], False)

            response = await self.admin_client.set_log_colors(
                not settings["log_colors"]
            )
            self.assertEqual(response, not settings["log_colors"])

            response = await self.admin_client.set_log_colors(settings["log_colors"])
            self.assertEqual(response, settings["log_colors"])

            await self.asyncTearDown()

        @async_test
        async def test_set_locking_debug(self):
            await self.asyncSetUp()

            settings = await self.admin_client.get_settings()
            self.assertEqual(settings["log_colors"], False)

            response = await self.admin_client.set_locking_debug(
                not settings["locking_debug"]
            )
            self.assertEqual(response, not settings["locking_debug"])

            response = await self.admin_client.set_locking_debug(
                settings["locking_debug"]
            )
            self.assertEqual(response, settings["locking_debug"])

            await self.asyncTearDown()

        @async_test
        async def test_set_refcount_debug(self):
            await self.asyncSetUp()

            settings = await self.admin_client.get_settings()
            self.assertEqual(settings["log_colors"], False)

            response = await self.admin_client.set_refcount_debug(
                not settings["refcount_debug"]
            )
            self.assertEqual(response, not settings["refcount_debug"])

            response = await self.admin_client.set_refcount_debug(
                settings["refcount_debug"]
            )
            self.assertEqual(response, settings["refcount_debug"])

            await self.asyncTearDown()

        @async_test
        async def test_set_libnice_debug(self):
            await self.asyncSetUp()

            settings = await self.admin_client.get_settings()
            self.assertEqual(settings["log_colors"], False)

            response = await self.admin_client.set_libnice_debug(
                not settings["libnice_debug"]
            )
            self.assertEqual(response, not settings["libnice_debug"])

            response = await self.admin_client.set_libnice_debug(
                settings["libnice_debug"]
            )
            self.assertEqual(response, settings["libnice_debug"])

            await self.asyncTearDown()

        @async_test
        async def test_set_min_nack_queue(self):
            await self.asyncSetUp()

            settings = await self.admin_client.get_settings()
            self.assertEqual(settings["log_colors"], False)

            response = await self.admin_client.set_min_nack_queue(
                settings["min_nack_queue"] + 1
            )
            self.assertEqual(response, settings["min_nack_queue"] + 1)

            response = await self.admin_client.set_min_nack_queue(
                settings["min_nack_queue"]
            )
            self.assertEqual(response, settings["min_nack_queue"])

            await self.asyncTearDown()

        @async_test
        async def test_set_no_media_timer(self):
            await self.asyncSetUp()

            settings = await self.admin_client.get_settings()
            self.assertEqual(settings["log_colors"], False)

            response = await self.admin_client.set_no_media_timer(
                settings["no_media_timer"] + 1
            )
            self.assertEqual(response, settings["no_media_timer"] + 1)

            response = await self.admin_client.set_no_media_timer(
                settings["no_media_timer"]
            )
            self.assertEqual(response, settings["no_media_timer"])

            await self.asyncTearDown()

        @async_test
        async def test_set_slowlink_threshold(self):
            await self.asyncSetUp()

            settings = await self.admin_client.get_settings()
            self.assertEqual(settings["log_colors"], False)

            response = await self.admin_client.set_slowlink_threshold(
                settings["slowlink_threshold"] + 1
            )
            self.assertEqual(response, settings["slowlink_threshold"] + 1)

            response = await self.admin_client.set_slowlink_threshold(
                settings["slowlink_threshold"]
            )
            self.assertEqual(response, settings["slowlink_threshold"])

            await self.asyncTearDown()

        @async_test
        async def test_list_tokens(self):
            await self.asyncSetUp()

            tokens = await self.admin_client.list_tokens()
            self.assertListEqual(tokens, [])

            await self.asyncTearDown()

        @async_test
        async def test_add_and_remove_token(self):
            await self.asyncSetUp()

            tokens = await self.admin_client.list_tokens()
            self.assertListEqual(tokens, [])

            token_test = "123123"

            token = await self.admin_client.add_token(token=token_test)
            self.assertEqual(token, token_test)

            response = await self.admin_client.remove_token(token=token_test)
            self.assertTrue(response)

            await self.asyncTearDown()

        @async_test
        async def test_allow_token(self):
            await self.asyncSetUp()

            tokens = await self.admin_client.list_tokens()
            self.assertListEqual(tokens, [])

            token_test = "123123"

            token = await self.admin_client.add_token(
                token=token_test, plugins=["janus.plugin.echotest"]
            )
            self.assertEqual(token, token_test)

            plugin_permissions = ["janus.plugin.echotest", "janus.plugin.streaming"]
            response = await self.admin_client.allow_token(
                token=token_test,
                plugins=plugin_permissions,
            )
            self.assertListEqual(response, plugin_permissions)

            response = await self.admin_client.remove_token(token=token_test)
            self.assertTrue(response)

            await self.asyncTearDown()

        @async_test
        async def test_disallow_token(self):
            await self.asyncSetUp()

            tokens = await self.admin_client.list_tokens()
            self.assertListEqual(tokens, [])

            token_test = "123123"

            token = await self.admin_client.add_token(
                token=token_test,
                plugins=[
                    "janus.plugin.audiobridge",
                    "janus.plugin.echolua",
                    "janus.plugin.videoroom",
                    "janus.plugin.echojs",
                    "janus.plugin.voicemail",
                    "janus.plugin.nosip",
                    "janus.plugin.videocall",
                    "janus.plugin.textroom",
                    "janus.plugin.echotest",
                    "janus.plugin.streaming",
                    "janus.plugin.recordplay",
                    "janus.plugin.sip",
                ],
            )
            self.assertEqual(token, token_test)

            plugin_permissions = ["janus.plugin.echotest", "janus.plugin.streaming"]
            response = await self.admin_client.disallow_token(
                token=token_test,
                plugins=plugin_permissions,
            )
            self.assertListEqual(
                response,
                [
                    "janus.plugin.audiobridge",
                    "janus.plugin.echolua",
                    "janus.plugin.videoroom",
                    "janus.plugin.echojs",
                    "janus.plugin.voicemail",
                    "janus.plugin.nosip",
                    "janus.plugin.videocall",
                    "janus.plugin.textroom",
                    "janus.plugin.recordplay",
                    "janus.plugin.sip",
                ],
            )

            response = await self.admin_client.remove_token(token=token_test)
            self.assertTrue(response)

            await self.asyncTearDown()


class TestTransportHttp(BaseTestClass.TestClass):
    server_url = urljoin(
        os.getenv("JANUS_HTTP_ADMIN_URL", ""),
        os.getenv("JANUS_HTTP_ADMIN_PATH", ""),
    )
    admin_secret = os.getenv("JANUS_ADMIN_SECRET", "")


class TestTransportWebsocket(BaseTestClass.TestClass):
    server_url = os.getenv("JANUS_WS_ADMIN_URL", "")
    admin_secret = os.getenv("JANUS_ADMIN_SECRET", "")
