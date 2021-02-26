
import asyncio
import websockets
import json
import uuid
from typing import Any, Generator, List, Optional, Sequence, Tuple, Type, cast

class JanusClient:
    def __init__(self, uri: str = ""):
        self.uri = uri
        self.received_transactions = dict()
        self.message_received_notifier = asyncio.Condition()
        self.ws = None

    async def connect(self, **kwargs: Any) -> None:
        print("Connecting to: ", self.uri)
        # self.ws = await websockets.connect(self.uri, ssl=ssl_context)
        self.ws = await websockets.connect(self.uri, subprotocols=["janus-protocol"], **kwargs)
        self.receive_message_task = asyncio.create_task(self.receive_message())
        print("Connected")

    async def disconnect(self):
        print("Disconnecting")
        self.receive_message_task.cancel()
        await self.ws.close()

    async def receive_message(self):
        assert self.ws
        async for response_raw in self.ws:
            response = json.loads(response_raw)
            if "transaction" in response:
                async with self.message_received_notifier:
                    self.received_transactions[response["transaction"]] = response
                    self.message_received_notifier.notify_all()
            else:
                self.emit_event(response)

    async def send(self, message: dict, ack: bool=False) -> dict():
        transaction_id = uuid.uuid4().hex
        message["transaction"] = transaction_id
        print(json.dumps(message))
        await self.ws.send(json.dumps(message))
        while True:
            try:
                response = await asyncio.wait_for(self.get_transaction_reply(transaction_id), 5)
                while ack and response["janus"] == "ack":
                    response = await asyncio.wait_for(self.get_transaction_reply(transaction_id), 5)
                print(response)
                return response
            except TimeoutError as e:
                print(e)
                print("Receive timeout")
                break

    async def get_transaction_reply(self, transaction_id):
        async with self.message_received_notifier:
            await self.message_received_notifier.wait_for(lambda: transaction_id in self.received_transactions)
            return self.received_transactions.pop(transaction_id)

    def emit_event(self, event_response: dict):
        print(event_response)