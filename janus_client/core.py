
import asyncio
import websockets
import json
import uuid

'''
Architecture design to handle Janus transactions and events
Assumption 1: All transaction ids are unique, and they will always get
    at least one reply when there are no network errors
So to handle transactions, it will be tracked in JanusClient only.
To handle events, it will be passed top down to all matching session id
    and plugin handle id.
Each node down the tree with JanusClient as root, including JanusClient itself,
shall have:
1. handle_async_response method

E.g.
class JanusSession
    def handle_async_response(self, response):
        pass
'''

class JanusClient:
    def __init__(self, uri: str = ""):
        self.uri = uri
        self.transactions = dict()
        # self.message_received_notifier = asyncio.Condition()
        self.ws = None
        self.sessions = dict()

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

    # async def add_transaction_response(self, response: dict) -> None:
    #     if response["transaction"] in self.transactions:
    #         await self.transactions[response["transaction"]].put(response)
    #     # # Only add the response if transaction ID is found
    #     # if response["transaction"] in self.transactions:
    #     #     async with self.message_received_notifier:
    #     #         self.transactions[response["transaction"]].put(response)
    #     #         self.message_received_notifier.notify_all()

    # async def get_transaction_reply(self, transaction_id):
    #     return await self.transactions[transaction_id].get()
    #     # async with self.message_received_notifier:
    #     #     # Wait until transaction contains message
    #     #     await self.message_received_notifier.wait_for(lambda: not self.transactions[transaction_id].empty())
    #     #     # Get and return the message
    #     #     return await self.transactions[transaction_id].get()

    def is_async_response(self, response):
        janus_type = response["janus"]
        return ((janus_type == "event")
            or (janus_type == "detached")
            or (janus_type == "webrtcup")
            or (janus_type == "media")
            or (janus_type == "slowlink")
            or (janus_type == "hangup"))

    async def receive_message(self):
        assert self.ws
        async for message_raw in self.ws:
            response = json.loads(message_raw)
            if self.is_async_response(response):
                self.handle_async_response(response)
            else:
                # WARNING: receive_message task will break with printing exception
                #   when entering here without a transaction in response.
                #   It happens when the asynchronous event is not recognized in
                #   self.is_async_response()
                # TODO: Find out how to print exceptions in created tasks
                if response["transaction"] in self.transactions:
                    await self.transactions[response["transaction"]].put(response)

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
        # Assumption: there will be one and only one synchronous reply for a transaction.
        #   Other replies with the same transaction ID are asynchronous.
        response = await self.transactions[transaction_id].get()
        print("Transaction reply: ", response)

        # Transaction complete, delete it
        del self.transactions[transaction_id]
        return response

    def handle_async_response(self, response: dict):
        if "session_id" in response:
            # This is response for session or plugin handle
            if response["session_id"] in self.sessions:
                self.sessions[response["session_id"]].handle_async_response(response)
            else:
                print("Got response for session but session not found. Session ID:", response["session_id"])
                print("Unhandeled response:", response)
        else:
            # This is response for self
            print("Async event for Janus client core:", response)

    async def create_session(self, session_type: object):
        response = await self.send({
            "janus": "create",
        })
        session = session_type(client=self, session_id=response["data"]["id"])
        self.sessions[session.id] = session
        return session

    def destroy_session(self, session):
        del self.sessions[session.id]