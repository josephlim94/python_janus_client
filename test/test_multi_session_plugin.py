import unittest
import logging
import asyncio

from janus_client import JanusTransport, JanusSession

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

        # async def test_1_1_N(self):
        #     """
        #     1 transport. transport:session = 1:1
        #     1 session. session:plugin = 1:N
        #     3 plugin
        #     """

        #     session_1 = JanusSession(transport=self.transport)
        #     session_2 = JanusSession(transport=self.transport)
        #     session_3 = JanusSession(transport=self.transport)

        #     response_list = await asyncio.gather(
        #         session_1.send(
        #             {"janus": "keepalive"},
        #             response_handler=lambda res: res if res["janus"] == "ack" else None,
        #         ),
        #         session_2.send(
        #             {"janus": "keepalive"},
        #             response_handler=lambda res: res if res["janus"] == "ack" else None,
        #         ),
        #         session_3.send(
        #             {"janus": "keepalive"},
        #             response_handler=lambda res: res if res["janus"] == "ack" else None,
        #         ),
        #     )

        #     self.assertEqual(response_list[0]["janus"], "ack")
        #     self.assertEqual(response_list[1]["janus"], "ack")
        #     self.assertEqual(response_list[2]["janus"], "ack")

        #     await asyncio.gather(
        #         session_1.destroy(), session_2.destroy(), session_3.destroy()
        #     )

        async def test_1_N_1(self):
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


class TestTransportHttps(BaseTestClass.TestClass):
    server_url = "https://janusmy.josephgetmyip.com/janusbase/janus"


class TestTransportWebsocketSecure(BaseTestClass.TestClass):
    server_url = "wss://janusmy.josephgetmyip.com/janusbasews/janus"
