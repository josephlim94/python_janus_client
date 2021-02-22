
import ssl
import asyncio
import websockets
import json
from concurrent.futures import TimeoutError
import random

# ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
# ssl_context.check_hostname = False
# ssl_context.verify_mode = ssl.CERT_NONE

random.seed(123)

class JanusClient:
    def __init__(self, uri: str = ""):
        self.uri = uri
        self.received_transactions = dict()
        self.message_received_notifier = asyncio.Condition()

    async def connect(self) -> None:
        print("Connecting to: ", self.uri)
        # self.ws = await websockets.connect(self.uri, ssl=ssl_context)
        self.ws = await websockets.connect(self.uri, subprotocols=["janus-protocol"])
        self.receive_message_task = asyncio.create_task(self.receive_message())
        print("Connected")

    async def disconnect(self):
        print("Disconnecting")
        self.receive_message_task.cancel()
        await self.ws.close()

    async def receive_message(self):
        while True:
            response = json.loads(await self.ws.recv())
            if "transaction" in response:
                async with self.message_received_notifier:
                    self.received_transactions[response["transaction"]] = response
                    self.message_received_notifier.notify_all()
            else:
                self.emit_event(response)

    async def send(self, message: dict) -> dict():
        transaction_id = str(random.randint(0, 9999))
        message["transaction"] = transaction_id
        await self.ws.send(json.dumps(message))
        while True:
            try:
                response = await asyncio.wait_for(self.get_transaction_reply(transaction_id), 5)
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

async def create_plugin(client, session_id):
    # Attach plugin
    response_plugin = await client.send({
        "janus": "attach",
        "session_id": session_id,
        "plugin": "janus.plugin.echotest",
    })
    print(response_plugin)
    if response_plugin["janus"] == "success":
        # Plugin attached
        # Destroy plugin
        response_detach = await client.send({
            "janus": "detach",
            "session_id": session_id,
            "handle_id": response_plugin["data"]["id"],
        })
        print(response_detach)

async def main():
    client = JanusClient("ws://lt.limmengkiat.name.my/janusws/")
    await client.connect()
    # Create session
    response = await client.send({
        "janus": "create",
    })
    print(response)
    if response["janus"] == "success":
        # Session created
        # # Attach plugin
        # response_plugin = await client.send({
        #     "janus": "attach",
        #     "session_id": response["data"]["id"],
        #     "plugin": "janus.plugin.echotest",
        # })
        # print(response_plugin)
        # if response_plugin["janus"] == "success":
        #     # Plugin attached
        #     # Destroy plugin
        #     response_detach = await client.send({
        #         "janus": "detach",
        #         "session_id": response["data"]["id"],
        #         "handle_id": response_plugin["data"]["id"],
        #     })
        #     print(response_detach)
        await asyncio.gather(create_plugin(client, response["data"]["id"]), create_plugin(client, response["data"]["id"]))
        # Destroy session
        reponse_destroy = await client.send({
            "janus": "destroy",
            "session_id": response["data"]["id"],
        })
        print(reponse_destroy)
    await client.disconnect()
    print("End of main")

asyncio.run(main())