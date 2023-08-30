import logging
import asyncio
from dataclasses import dataclass
from typing import Dict

import aiohttp

from .transport import JanusTransport


logger = logging.getLogger(__name__)


@dataclass
class ReceiverTask:
    task: asyncio.Task
    destroyed_event: asyncio.Event


class JanusTransportHTTP(JanusTransport):
    """Janus transport through HTTP"""

    __receive_response_task_map: Dict[int, ReceiverTask]
    __api_secret: str
    __token: str

    def __init__(
        self, base_url: str, api_secret: str = None, token: str = None, **kwargs: dict
    ):
        super().__init__(base_url=base_url, api_secret=api_secret, token=token)

        self.__receive_response_task_map = dict()
        # HTTP transport needs these for long polling
        self.__api_secret = api_secret
        self.__token = token

    async def _connect(self):
        pass

    async def _disconnect(self):
        pass

    def __build_url(self, session_id: int = None, handle_id: int = None) -> str:
        url = f"{self.base_url}"

        if session_id:
            url = f"{url}/{session_id}"

            if handle_id:
                url = f"{url}/{handle_id}"

        return url

    async def info(self) -> Dict:
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(f"{self.base_url}/info") as response:
                return await response.json()

    async def _send(
        self,
        message: Dict,
    ) -> None:
        session_id = message.get("session_id")
        handle_id = message.get("handle_id")

        async with aiohttp.ClientSession() as http_session:
            async with http_session.post(
                url=self.__build_url(session_id=session_id, handle_id=handle_id),
                json=message,
            ) as response:
                response.raise_for_status()

                response_dict = await response.json()

                # if "error" in response_dict:
                #     raise Exception(response_dict)

                # # There must be a transaction ID
                # response_transaction_id = response_dict["transaction"]

                # Fake receive
                # # We will immediately get a response in the HTTP response, so need
                # # to put this into the queue
                # await self.put_response(
                #     transaction_id=response_transaction_id, response=response_dict
                # )
                await self.receive(response=response_dict)

    def session_receive_response_done_cb(
        self, task: asyncio.Task, context=None
    ) -> None:
        try:
            # Check if any exceptions are raised
            task.exception()
        except asyncio.CancelledError:
            logger.info("Receive message task ended")
        except asyncio.InvalidStateError:
            logger.info("receive_message_done_cb called with invalid state")
        except Exception as err:
            logger.error(err)

    async def session_receive_response(
        self, session_id: str, destroyed_event: asyncio.Event
    ) -> None:
        url_params = {}
        if self.__api_secret:
            url_params["apisecret"] = self.__api_secret
        if self.__token:
            url_params["token"] = self.__token

        async with aiohttp.ClientSession() as http_session:
            while not destroyed_event.is_set():
                async with http_session.get(
                    url=self.__build_url(session_id=session_id),
                    params=url_params,
                ) as response:
                    # Maybe session is destroyed during http request
                    if destroyed_event.is_set():
                        break

                    response.raise_for_status()

                    response_dict = await response.json()

                    if "error" in response_dict:
                        raise Exception(response_dict)

                    if response_dict["janus"] == "keepalive":
                        continue

                    await self.receive(response=response_dict)

    async def dispatch_session_created(self, session_id: str) -> None:
        logger.info(f"Create session_receive_response task ({session_id})")
        destroyed_event = asyncio.Event()
        task = asyncio.create_task(
            self.session_receive_response(
                session_id=session_id, destroyed_event=destroyed_event
            )
        )
        task.add_done_callback(self.session_receive_response_done_cb)
        self.__receive_response_task_map[session_id] = ReceiverTask(
            task=task, destroyed_event=destroyed_event
        )

    async def dispatch_session_destroyed(self, session_id: int) -> None:
        if session_id not in self.__receive_response_task_map:
            logger.warn(f"Session receive response task not found for {session_id}")

        logger.info(f"Destroy session_receive_response task ({session_id})")
        receiver_task = self.__receive_response_task_map[session_id]
        # Don't use task.cancel() to avoid
        # Exception ignored in: <function _ProactorBasePipeTransport.__del__ at 0x0000027A269465F0>
        receiver_task.destroyed_event.set()

        # Destroying sessions could cost some time because it needs to
        # wait for the long-poll request to complete
        await asyncio.wait([receiver_task.task])


def protocol_matcher(base_url: str):
    return base_url.startswith(("http://", "https://"))


JanusTransport.register_transport(
    protocol_matcher=protocol_matcher, transport_cls=JanusTransportHTTP
)
