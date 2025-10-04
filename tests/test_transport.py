import unittest
import logging
import asyncio
import os
from urllib.parse import urljoin

from janus_client import JanusTransport, JanusSession
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

            response = await self.transport.ping()
            self.assertEqual(response["janus"], "pong")

            await self.asyncTearDown()

        @async_test
        async def test_info(self):
            await self.asyncSetUp()

            response = await self.transport.info()
            self.assertEqual(response["janus"], "server_info")
            self.assertEqual(response["name"], "Janus WebRTC Server")

            await self.asyncTearDown()

        @async_test
        async def test_session(self):
            await self.asyncSetUp()

            session = JanusSession(transport=self.transport)

            message_transaction = await session.send(
                {"janus": "keepalive"},
            )
            response = await message_transaction.get({"janus": "ack"})
            await message_transaction.done()
            self.assertEqual(response["janus"], "ack")

            await session.destroy()

            await self.asyncTearDown()

        @async_test
        async def test_session_fail_auth(self):
            session = JanusSession(
                base_url=self.server_url,
            )
            with self.assertRaisesRegex(Exception, "Create session fail: {'code': 403"):
                await session.create()
            await session.transport.disconnect()

            session = JanusSession(
                base_url=self.server_url,
                api_secret="asdewqzxc",
            )
            with self.assertRaisesRegex(Exception, "Create session fail: {'code': 403"):
                await session.create()
            await session.transport.disconnect()

            session = JanusSession(
                base_url=self.server_url,
                api_secret=os.getenv("JANUS_API_SECRET", ""),
            )
            await session.create()
            await session.destroy()


class TestTransportHttp(BaseTestClass.TestClass):
    server_url = urljoin(
        os.getenv("JANUS_HTTP_URL", ""),
        os.getenv("JANUS_HTTP_BASE_PATH", ""),
    )


class TestTransportWebsocket(BaseTestClass.TestClass):
    server_url = os.getenv("JANUS_WS_URL", "")
