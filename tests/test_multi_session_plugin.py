import unittest
import logging
import asyncio
import os
from urllib.parse import urljoin

from janus_client import JanusTransport, JanusSession, JanusVideoRoomPlugin
from tests.util import async_test

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
logger = logging.getLogger()

ut_api_secret = os.getenv("JANUS_API_SECRET", "")


class BaseTestClass:
    class TestClass(unittest.TestCase):
        server_url: str

        async def asyncSetUp(self) -> None:
            self.transport = JanusTransport.create_transport(
                base_url=self.server_url, api_secret=ut_api_secret
            )
            await self.transport.connect()

        async def asyncTearDown(self) -> None:
            await self.transport.disconnect()
            # https://docs.aiohttp.org/en/stable/client_advanced.html#graceful-shutdown
            # Working around to avoid "Exception ignored in: <function _ProactorBasePipeTransport.__del__ at 0x0000024A04C60280>"
            await asyncio.sleep(0.250)

        @async_test
        async def test_0_1_1(self):
            """
            0 transport. transport created automatically by session
            1 session. session:plugin = 1:1
            1 plugin
            """

            await self.asyncSetUp()

            room_id = 1234

            session = JanusSession(base_url=self.server_url, api_secret=ut_api_secret)

            plugin = JanusVideoRoomPlugin()

            await plugin.attach(session=session)

            await plugin.join(room_id, 111, "aaa")

            await plugin.leave()

            await plugin.destroy()

            await session.destroy()

            await self.asyncTearDown()

        @async_test
        async def test_1_1_1(self):
            """
            1 transport. transport:session = 1:1
            1 session. session:plugin = 1:1
            1 plugin
            """

            await self.asyncSetUp()

            room_id = 1234

            session = JanusSession(transport=self.transport)

            plugin = JanusVideoRoomPlugin()

            await plugin.attach(session=session)

            await plugin.join(room_id, 111, "aaa")

            await plugin.leave()

            await plugin.destroy()

            await session.destroy()

            await self.asyncTearDown()

        @async_test
        async def test_1_N_0(self):
            """
            1 transport. transport:session = 1:N
            3 session. session:plugin = 1:1
            """

            await self.asyncSetUp()

            session_1 = JanusSession(transport=self.transport)
            session_2 = JanusSession(transport=self.transport)
            session_3 = JanusSession(transport=self.transport)

            message_transaction_list = await asyncio.gather(
                session_1.send(
                    {"janus": "keepalive"},
                ),
                session_2.send(
                    {"janus": "keepalive"},
                ),
                session_3.send(
                    {"janus": "keepalive"},
                ),
            )
            response_1 = await message_transaction_list[0].get({"janus": "ack"})
            response_2 = await message_transaction_list[1].get({"janus": "ack"})
            response_3 = await message_transaction_list[2].get({"janus": "ack"})
            await message_transaction_list[0].done()
            await message_transaction_list[1].done()
            await message_transaction_list[2].done()

            self.assertEqual(response_1["janus"], "ack")
            self.assertEqual(response_2["janus"], "ack")
            self.assertEqual(response_3["janus"], "ack")

            await asyncio.gather(
                session_1.destroy(), session_2.destroy(), session_3.destroy()
            )

            await self.asyncTearDown()

        @async_test
        async def test_0_N_0(self):
            """
            0 transport. transport created automatically by session
            3 session. session:plugin = 1:1
            0 plugin
            """

            await self.asyncSetUp()

            session_1 = JanusSession(base_url=self.server_url, api_secret=ut_api_secret)
            session_2 = JanusSession(base_url=self.server_url, api_secret=ut_api_secret)
            session_3 = JanusSession(base_url=self.server_url, api_secret=ut_api_secret)

            message_transaction_list = await asyncio.gather(
                session_1.send(
                    {"janus": "keepalive"},
                ),
                session_2.send(
                    {"janus": "keepalive"},
                ),
                session_3.send(
                    {"janus": "keepalive"},
                ),
            )
            response_1 = await message_transaction_list[0].get({"janus": "ack"})
            response_2 = await message_transaction_list[1].get({"janus": "ack"})
            response_3 = await message_transaction_list[2].get({"janus": "ack"})
            await message_transaction_list[0].done()
            await message_transaction_list[1].done()
            await message_transaction_list[2].done()

            self.assertEqual(response_1["janus"], "ack")
            self.assertEqual(response_2["janus"], "ack")
            self.assertEqual(response_3["janus"], "ack")

            await asyncio.gather(
                session_1.destroy(), session_2.destroy(), session_3.destroy()
            )

            await self.asyncTearDown()

        @async_test
        async def test_1_1_N(self):
            """
            1 transport. transport:session = 1:1
            1 session. session:plugin = 1:N
            3 plugin
            """

            await self.asyncSetUp()

            room_id = 1234

            session = JanusSession(transport=self.transport)

            plugin_1 = JanusVideoRoomPlugin()
            plugin_2 = JanusVideoRoomPlugin()
            plugin_3 = JanusVideoRoomPlugin()

            await asyncio.gather(
                plugin_1.attach(session=session),
                plugin_2.attach(session=session),
                plugin_3.attach(session=session),
            )

            await asyncio.gather(
                plugin_1.join(room_id, 111, "aaa"),
                plugin_2.join(room_id, 222, "bbb"),
                plugin_3.join(room_id, 333, "ccc"),
            )

            await asyncio.gather(
                plugin_1.leave(),
                plugin_2.leave(),
                plugin_3.leave(),
            )

            await asyncio.gather(
                plugin_1.destroy(),
                plugin_2.destroy(),
                plugin_3.destroy(),
            )

            await session.destroy()

            await self.asyncTearDown()

        @async_test
        async def test_1_N_N(self):
            """
            1 transport. transport:session = 1:N
            3 session. session:plugin = 1:1
            """

            await self.asyncSetUp()

            async def test_N_plugin(session, publisher_id):
                room_id = 1234

                plugin_1 = JanusVideoRoomPlugin()
                plugin_2 = JanusVideoRoomPlugin()
                plugin_3 = JanusVideoRoomPlugin()

                await asyncio.gather(
                    plugin_1.attach(session=session),
                    plugin_2.attach(session=session),
                    plugin_3.attach(session=session),
                )

                await asyncio.gather(
                    plugin_1.join(room_id, publisher_id, "aaa"),
                    plugin_2.join(room_id, publisher_id + 1, "bbb"),
                    plugin_3.join(room_id, publisher_id + 2, "ccc"),
                )

                await asyncio.gather(
                    plugin_1.leave(),
                    plugin_2.leave(),
                    plugin_3.leave(),
                )

                await asyncio.gather(
                    plugin_1.destroy(),
                    plugin_2.destroy(),
                    plugin_3.destroy(),
                )

            session_1 = JanusSession(transport=self.transport)
            session_2 = JanusSession(transport=self.transport)
            session_3 = JanusSession(transport=self.transport)

            message_transaction_list = await asyncio.gather(
                session_1.send(
                    {"janus": "keepalive"},
                ),
                session_2.send(
                    {"janus": "keepalive"},
                ),
                session_3.send(
                    {"janus": "keepalive"},
                ),
            )
            response_1 = await message_transaction_list[0].get({"janus": "ack"})
            response_2 = await message_transaction_list[1].get({"janus": "ack"})
            response_3 = await message_transaction_list[2].get({"janus": "ack"})
            await message_transaction_list[0].done()
            await message_transaction_list[1].done()
            await message_transaction_list[2].done()

            self.assertEqual(response_1["janus"], "ack")
            self.assertEqual(response_2["janus"], "ack")
            self.assertEqual(response_3["janus"], "ack")

            await asyncio.gather(
                test_N_plugin(session=session_1, publisher_id=111),
                test_N_plugin(session=session_2, publisher_id=222),
                test_N_plugin(session=session_3, publisher_id=333),
            )

            await asyncio.gather(
                session_1.destroy(), session_2.destroy(), session_3.destroy()
            )

            await self.asyncTearDown()

        @async_test
        async def test_0_N_N(self):
            """
            1 transport. transport:session = 1:N
            3 session. session:plugin = 1:1
            """

            await self.asyncSetUp()

            async def test_N_plugin(session, publisher_id):
                room_id = 1234

                plugin_1 = JanusVideoRoomPlugin()
                plugin_2 = JanusVideoRoomPlugin()
                plugin_3 = JanusVideoRoomPlugin()

                await asyncio.gather(
                    plugin_1.attach(session=session),
                    plugin_2.attach(session=session),
                    plugin_3.attach(session=session),
                )

                await asyncio.gather(
                    plugin_1.join(room_id, publisher_id, "aaa"),
                    plugin_2.join(room_id, publisher_id + 1, "bbb"),
                    plugin_3.join(room_id, publisher_id + 2, "ccc"),
                )

                await asyncio.gather(
                    plugin_1.leave(),
                    plugin_2.leave(),
                    plugin_3.leave(),
                )

                await asyncio.gather(
                    plugin_1.destroy(),
                    plugin_2.destroy(),
                    plugin_3.destroy(),
                )

            session_1 = JanusSession(base_url=self.server_url, api_secret=ut_api_secret)
            session_2 = JanusSession(base_url=self.server_url, api_secret=ut_api_secret)
            session_3 = JanusSession(base_url=self.server_url, api_secret=ut_api_secret)

            message_transaction_list = await asyncio.gather(
                session_1.send(
                    {"janus": "keepalive"},
                ),
                session_2.send(
                    {"janus": "keepalive"},
                ),
                session_3.send(
                    {"janus": "keepalive"},
                ),
            )
            response_1 = await message_transaction_list[0].get({"janus": "ack"})
            response_2 = await message_transaction_list[1].get({"janus": "ack"})
            response_3 = await message_transaction_list[2].get({"janus": "ack"})
            await message_transaction_list[0].done()
            await message_transaction_list[1].done()
            await message_transaction_list[2].done()

            self.assertEqual(response_1["janus"], "ack")
            self.assertEqual(response_2["janus"], "ack")
            self.assertEqual(response_3["janus"], "ack")

            await asyncio.gather(
                test_N_plugin(session=session_1, publisher_id=111),
                test_N_plugin(session=session_2, publisher_id=222),
                test_N_plugin(session=session_3, publisher_id=333),
            )

            await asyncio.gather(
                session_1.destroy(), session_2.destroy(), session_3.destroy()
            )

            await self.asyncTearDown()


class TestTransportHttp(BaseTestClass.TestClass):
    server_url = urljoin(
        os.getenv("JANUS_HTTP_URL", ""),
        os.getenv("JANUS_HTTP_BASE_PATH", ""),
    )


class TestTransportWebsocket(BaseTestClass.TestClass):
    server_url = os.getenv("JANUS_WS_URL", "")
