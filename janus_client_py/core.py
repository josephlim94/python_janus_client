
import asyncio
import websockets
import json
import uuid

class JanusClient:
    def __init__(self, uri: str = ""):
        self.uri = uri
        self.transactions = dict()
        # self.message_received_notifier = asyncio.Condition()
        self.ws = None

    async def connect(self, **kwargs: object) -> None:
        print("Connecting to: ", self.uri)
        # self.ws = await websockets.connect(self.uri, ssl=ssl_context)
        self.ws = await websockets.connect(self.uri, subprotocols=["janus-protocol"], **kwargs)
        self.receive_message_task = asyncio.create_task(self.receive_message())
        print("Connected")

    async def disconnect(self):
        print("Disconnecting")
        self.receive_message_task.cancel()
        await self.ws.close()

    async def add_transaction_response(self, response: dict) -> None:
        if response["transaction"] in self.transactions:
            await self.transactions[response["transaction"]].put(response)
        # # Only add the response if transaction ID is found
        # if response["transaction"] in self.transactions:
        #     async with self.message_received_notifier:
        #         self.transactions[response["transaction"]].put(response)
        #         self.message_received_notifier.notify_all()

    async def get_transaction_reply(self, transaction_id):
        return await self.transactions[transaction_id].get()
        # async with self.message_received_notifier:
        #     # Wait until transaction contains message
        #     await self.message_received_notifier.wait_for(lambda: not self.transactions[transaction_id].empty())
        #     # Get and return the message
        #     return await self.transactions[transaction_id].get()

    async def receive_message(self):
        assert self.ws
        async for message_raw in self.ws:
            response = json.loads(message_raw)
            if "transaction" in response:
                await self.add_transaction_response(response)
            else:
                self.emit_event(response)

    async def send(self, message: dict, **kwargs) -> dict():
        # Create transaction
        transaction_id = uuid.uuid4().hex
        message["transaction"] = transaction_id
        # Transaction ID must be in the dict to receive response
        self.transactions[transaction_id] = asyncio.Queue()

        # Send the message
        print(json.dumps(message))
        await self.ws.send(json.dumps(message))

        # Wait for response
        response = None
        if "complete_condition" in kwargs:
            complete_condition = kwargs["complete_condition"]
            response = await self.get_transaction_reply(transaction_id)
            while not complete_condition(response):
                response = await self.get_transaction_reply(transaction_id)
        else:
            response = await self.get_transaction_reply(transaction_id)
        print("Transaction reply: ", response)

        # Transaction complete, delete it
        del self.transactions[transaction_id]
        return response
        # while True:
        #     try:
        #         response = await asyncio.wait_for(self.get_transaction_reply(transaction_id), 5)
        #         while ack and response["janus"] == "ack":
        #             response = await asyncio.wait_for(self.get_transaction_reply(transaction_id), 5)
        #         print(response)
        #         # Transaction complete, delete it
        #         del self.transactions[transaction_id]
        #         return response
        #     except TimeoutError as e:
        #         print(e)
        #         print("Receive timeout")
        #         break

    def emit_event(self, event_response: dict):
        print(event_response)

    async def create_session(self, session_type: object):
        response = await self.send({
            "janus": "create",
        })
        return session_type(client=self, session_id=response["data"]["id"])