import logging
from typing import Any
import asyncio
import json
import traceback

import websockets

from .transport import JanusTransport


logger = logging.getLogger(__name__)


class JanusTransportWebsocket(JanusTransport):
    """Janus transport through HTTP

    Manage Sessions and Transactions
    """

    ws: websockets.WebSocketClientProtocol
    subprotocol: str
    connected: bool
    receiving_message: bool
    receive_message_task: asyncio.Task
    receive_message_task_started: asyncio.Event

    def __init__(self, **kwargs: dict):
        super().__init__(**kwargs)

        self.connected = False
        self.receiving_message = False
        self.receive_message_task = None
        self.receive_message_task_started = asyncio.Event()

        if "subprotocol" in kwargs:
            self.subprotocol = kwargs["subprotocol"]
        else:
            self.subprotocol = "janus-protocol"

    async def _connect(self, **kwargs: Any) -> None:
        """Connect to server

        All extra keyword arguments will be passed to websockets.connect
        """

        logger.info(f"Connecting to: {self.base_url}")

        self.ws = await websockets.connect(
            self.base_url,
            subprotocols=[websockets.Subprotocol(self.subprotocol)],
            **kwargs,
        )
        self.receive_message_task = asyncio.create_task(self.receive_message())
        self.receive_message_task.add_done_callback(self.receive_message_done_cb)
        await self.receive_message_task_started.wait()

        self.connected = True
        logger.info("Connected")

    async def _disconnect(self) -> None:
        logger.info("Disconnecting")
        self.receive_message_task.cancel()
        await asyncio.wait([self.receive_message_task])
        await self.ws.close()
        self.connected = False
        logger.info("Disconnected")

    def receive_message_done_cb(self, task: asyncio.Task, context=None) -> None:
        self.receiving_message = False
        try:
            # Check if any exceptions are raised
            # If it's CancelledError or InvalidStateError exception then they will be raised
            # else the exception in task will be returned
            exception = task.exception()
            if exception:
                logger.error(
                    "".join(
                        traceback.format_exception(
                            type(exception),
                            value=exception,
                            tb=exception.__traceback__,
                        )
                    )
                )
        except asyncio.CancelledError:
            logger.info("Receive message task ended")
        except asyncio.InvalidStateError:
            logger.info("receive_message_done_cb called with invalid state")

        self.connected = False

    async def receive_message(self) -> None:
        self.receiving_message = True
        self.receive_message_task_started.set()

        if not self.ws:
            raise Exception("Not connected to server.")

        async for message_raw in self.ws:
            response = json.loads(message_raw)

            await self.receive(response)

    async def _send(
        self,
        message: dict,
    ) -> None:
        if not self.connected:
            raise Exception("Must connect before any communication.")

        if not self.receiving_message:
            raise Exception("Websocket not receiving message")

        await self.ws.send(json.dumps(message))


def protocol_matcher(base_url: str):
    return base_url.startswith(("ws://", "wss://"))


JanusTransport.register_transport(
    protocol_matcher=protocol_matcher, transport_cls=JanusTransportWebsocket
)
