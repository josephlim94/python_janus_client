import unittest
import logging
import asyncio

from janus_client import JanusTransport, JanusSession, JanusVideoRoomPlugin

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
logger = logging.getLogger()


class BaseTestClass:
    class TestClass(unittest.IsolatedAsyncioTestCase):
        server_url: str

        async def asyncSetUp(self) -> None:
            self.transport = JanusTransport.create_transport(base_url=self.server_url)
            await self.transport.connect()

        async def asyncTearDown(self) -> None:
            await self.transport.disconnect()
            # https://docs.aiohttp.org/en/stable/client_advanced.html#graceful-shutdown
            # Working around to avoid "Exception ignored in: <function _ProactorBasePipeTransport.__del__ at 0x0000024A04C60280>"
            await asyncio.sleep(0.250)

        async def test_0_1_1(self):
            """
            0 transport. transport created automatically by session
            1 session. session:plugin = 1:1
            1 plugin
            """

            room_id = 1234

            session = JanusSession(base_url=self.server_url)

            plugin = JanusVideoRoomPlugin()

            await plugin.attach(session=session)

            await plugin.join(room_id, 111, "aaa")

            await plugin.leave()

            await plugin.destroy()

            await session.destroy()

        async def test_1_1_1(self):
            """
            1 transport. transport:session = 1:1
            1 session. session:plugin = 1:1
            1 plugin
            """

            room_id = 1234

            session = JanusSession(transport=self.transport)

            plugin = JanusVideoRoomPlugin()

            await plugin.attach(session=session)

            await plugin.join(room_id, 111, "aaa")

            await plugin.leave()

            await plugin.destroy()

            await session.destroy()

        async def test_1_N_0(self):
            """
            1 transport. transport:session = 1:N
            3 session. session:plugin = 1:1
            """

            session_1 = JanusSession(transport=self.transport)
            session_2 = JanusSession(transport=self.transport)
            session_3 = JanusSession(transport=self.transport)

            response_list = await asyncio.gather(
                session_1.send(
                    {"janus": "keepalive"},
                    response_handler=lambda res: res if res["janus"] == "ack" else None,
                ),
                session_2.send(
                    {"janus": "keepalive"},
                    response_handler=lambda res: res if res["janus"] == "ack" else None,
                ),
                session_3.send(
                    {"janus": "keepalive"},
                    response_handler=lambda res: res if res["janus"] == "ack" else None,
                ),
            )

            self.assertEqual(response_list[0]["janus"], "ack")
            self.assertEqual(response_list[1]["janus"], "ack")
            self.assertEqual(response_list[2]["janus"], "ack")

            await asyncio.gather(
                session_1.destroy(), session_2.destroy(), session_3.destroy()
            )

        async def test_0_N_0(self):
            """
            0 transport. transport created automatically by session
            3 session. session:plugin = 1:1
            0 plugin
            """

            session_1 = JanusSession(base_url=self.server_url)
            session_2 = JanusSession(base_url=self.server_url)
            session_3 = JanusSession(base_url=self.server_url)

            response_list = await asyncio.gather(
                session_1.send(
                    {"janus": "keepalive"},
                    response_handler=lambda res: res if res["janus"] == "ack" else None,
                ),
                session_2.send(
                    {"janus": "keepalive"},
                    response_handler=lambda res: res if res["janus"] == "ack" else None,
                ),
                session_3.send(
                    {"janus": "keepalive"},
                    response_handler=lambda res: res if res["janus"] == "ack" else None,
                ),
            )

            self.assertEqual(response_list[0]["janus"], "ack")
            self.assertEqual(response_list[1]["janus"], "ack")
            self.assertEqual(response_list[2]["janus"], "ack")

            await asyncio.gather(
                session_1.destroy(), session_2.destroy(), session_3.destroy()
            )

        async def test_1_1_N(self):
            """
            1 transport. transport:session = 1:1
            1 session. session:plugin = 1:N
            3 plugin
            """

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

        async def test_1_N_N(self):
            """
            1 transport. transport:session = 1:N
            3 session. session:plugin = 1:1
            """

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

            response_list = await asyncio.gather(
                session_1.send(
                    {"janus": "keepalive"},
                    response_handler=lambda res: res if res["janus"] == "ack" else None,
                ),
                session_2.send(
                    {"janus": "keepalive"},
                    response_handler=lambda res: res if res["janus"] == "ack" else None,
                ),
                session_3.send(
                    {"janus": "keepalive"},
                    response_handler=lambda res: res if res["janus"] == "ack" else None,
                ),
            )

            self.assertEqual(response_list[0]["janus"], "ack")
            self.assertEqual(response_list[1]["janus"], "ack")
            self.assertEqual(response_list[2]["janus"], "ack")

            await asyncio.gather(
                test_N_plugin(session=session_1, publisher_id=111),
                test_N_plugin(session=session_2, publisher_id=222),
                test_N_plugin(session=session_3, publisher_id=333),
            )

            await asyncio.gather(
                session_1.destroy(), session_2.destroy(), session_3.destroy()
            )

        async def test_0_N_N(self):
            """
            1 transport. transport:session = 1:N
            3 session. session:plugin = 1:1
            """

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

            session_1 = JanusSession(base_url=self.server_url)
            session_2 = JanusSession(base_url=self.server_url)
            session_3 = JanusSession(base_url=self.server_url)

            response_list = await asyncio.gather(
                session_1.send(
                    {"janus": "keepalive"},
                    response_handler=lambda res: res if res["janus"] == "ack" else None,
                ),
                session_2.send(
                    {"janus": "keepalive"},
                    response_handler=lambda res: res if res["janus"] == "ack" else None,
                ),
                session_3.send(
                    {"janus": "keepalive"},
                    response_handler=lambda res: res if res["janus"] == "ack" else None,
                ),
            )

            self.assertEqual(response_list[0]["janus"], "ack")
            self.assertEqual(response_list[1]["janus"], "ack")
            self.assertEqual(response_list[2]["janus"], "ack")

            await asyncio.gather(
                test_N_plugin(session=session_1, publisher_id=111),
                test_N_plugin(session=session_2, publisher_id=222),
                test_N_plugin(session=session_3, publisher_id=333),
            )

            await asyncio.gather(
                session_1.destroy(), session_2.destroy(), session_3.destroy()
            )


class TestTransportHttps(BaseTestClass.TestClass):
    server_url = "https://janusmy.josephgetmyip.com/janusbase/janus"


class TestTransportWebsocketSecure(BaseTestClass.TestClass):
    server_url = "wss://janusmy.josephgetmyip.com/janusbasews/janus"
