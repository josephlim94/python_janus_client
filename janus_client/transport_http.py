import logging
from typing import Any
import asyncio

import aiohttp

from .transport import JanusTransport


logger = logging.getLogger(__name__)


class JanusTransportHTTP(JanusTransport):
    """Janus transport through HTTP"""

    __receive_response_task_map: dict[int, asyncio.Task]

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        self.__receive_response_task_map: dict[int, asyncio.Task] = dict()

    async def connect(self) -> None:
        self.connected = True

    # async def disconnect(self) -> None:
    #     logger.info("Disconnecting")
    #     self.__asyncio_session = None
    #     self.connected = False
    #     logger.info("Disconnected")

    def __build_url(self, session_id: int = None, handle_id: int = None) -> str:
        url = f"{self.base_url}"

        if session_id:
            url = f"{url}/{session_id}"

            if handle_id:
                url = f"{url}/{handle_id}"

        return url

    async def info(self) -> dict:
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(f"{self.base_url}/info") as response:
                return await response.json()

    async def _send(
        self,
        message: dict,
    ) -> None:
        if not self.connected:
            raise Exception("Must connect before any communication.")

        session_id = message.get("session_id")
        handle_id = message.get("handle_id")

        async with aiohttp.ClientSession() as http_session:
            async with http_session.post(
                url=self.__build_url(session_id=session_id, handle_id=handle_id),
                json=message,
            ) as response:
                print("Status:", response.status)
                print("Content-type:", response.headers["content-type"])

                response.raise_for_status()

                response_dict = await response.json()

                if "error" in response_dict:
                    raise Exception(response_dict)

                # # There must be a transaction ID
                # response_transaction_id = response_dict["transaction"]

                # Fake receive
                # # We will immediately get a response in the HTTP response, so need
                # # to put this into the queue
                # await self.put_response(
                #     transaction_id=response_transaction_id, response=response_dict
                # )
                await self.receive(response=response_dict)

    async def session_receive_response(self, session_id: str) -> None:
        logger.info("start task")
        session_destroyed = False
        while not session_destroyed:
            logger.info("Start loop")
            async with aiohttp.ClientSession() as http_session:
                async with http_session.get(
                    url=self.__build_url(session_id=session_id),
                ) as response:
                    response.raise_for_status()

                    response_dict = await response.json()

                    if "error" in response_dict:
                        raise Exception(response_dict)

                    if response_dict["janus"] == "keepalive":
                        continue

                    self.receive(response=response_dict)

    async def dispatch_session_created(self, session_id: str) -> None:
        logger.info(f"Create session_receive_response task ({session_id})")
        task = asyncio.create_task(self.session_receive_response(session_id=session_id))
        self.__receive_response_task_map[session_id] = task

    async def dispatch_session_destroyed(self, session_id: int) -> None:
        if session_id not in self.__receive_response_task_map:
            logger.warn(f"Session receive response task not found for {session_id}")

        logger.info(f"Destroy session_receive_response task ({session_id})")
        self.__receive_response_task_map[session_id].cancel()


def protocol_matcher(base_url: str):
    return base_url.startswith(("http://", "https://"))


JanusTransport.register_transport(
    protocol_matcher=protocol_matcher, transport_cls=JanusTransportHTTP
)
