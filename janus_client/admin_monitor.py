import asyncio
import json
import uuid
from typing import Dict, Any

import websockets

import logging

logger = logging.getLogger(__name__)


"""
# Take note to enable admin API with websockets in Janus, for example:
# admin: {
#         admin_ws = true                         # Whether to enable the Admin API WebSockets API
#         admin_ws_port = 7188                    # Admin API WebSockets server port, if enabled
#         #admin_ws_interface = "eth0"            # Whether we should bind this server to a specific interface only
#         #admin_ws_ip = "192.168.0.1"            # Whether we should bind this server to a specific IP address only
#         admin_wss = true                        # Whether to enable the Admin API secure WebSockets
#         admin_wss_port = 7989                   # Admin API WebSockets server secure port, if enabled
#         #admin_wss_interface = "eth0"           # Whether we should bind this server to a specific interface only
#         #admin_wss_ip = "192.168.0.1"           # Whether we should bind this server to a specific IP address only
#         #admin_ws_acl = "127.,192.168.0."       # Only allow requests coming from this comma separated list of addresses
# }
"""


class JanusAdminMonitorClient:
    def __init__(self, uri: str, admin_secret: str):
        self.ws: websockets.WebSocketClientProtocol
        self.uri = uri
        self.admin_secret = admin_secret
        self.transactions: Dict[str, asyncio.Queue] = dict()

    async def connect(self, **kwargs: Any) -> None:
        logger.info(f"Connecting to: {self.uri}")
        # self.ws = await websockets.connect(self.uri, ssl=ssl_context)
        self.ws = await websockets.connect(
            self.uri,
            subprotocols=[websockets.Subprotocol("janus-admin-protocol")],
            **kwargs,
        )
        self.receive_message_task = asyncio.create_task(self.receive_message())
        logger.info("Connected")

    async def disconnect(self):
        logger.info("Disconnecting")
        self.receive_message_task.cancel()
        await self.ws.close()

    async def receive_message(self):
        assert self.ws
        async for message_raw in self.ws:
            response = json.loads(message_raw)
            # WARNING: receive_message task will break with logger.infoing exception
            #   when entering here without a transaction in response.
            #   It happens when the asynchronous event is not recognized in
            #   self.is_async_response()
            # TODO: Find out how to logger.info exceptions in created tasks
            if response["transaction"] in self.transactions:
                await self.transactions[response["transaction"]].put(response)

    async def send(self, message: dict, authenticate: bool = True) -> dict:
        # Create transaction
        transaction_id = uuid.uuid4().hex
        message["transaction"] = transaction_id
        # Transaction ID must be in the dict to receive response
        self.transactions[transaction_id] = asyncio.Queue()

        # Authentication
        if authenticate:
            message["admin_secret"] = self.admin_secret

        # Send the message
        logger.info(json.dumps(message))
        await self.ws.send(json.dumps(message))

        # Wait for response
        # Assumption: there will be one and only one synchronous reply for a transaction.
        #   Other replies with the same transaction ID are asynchronous.
        response = await self.transactions[transaction_id].get()
        logger.info(f"Transaction reply: {response}")

        # Transaction complete, delete it
        del self.transactions[transaction_id]
        return response

    async def info(self):
        # Doesn't require admin secret
        message = {"janus": "info"}
        return await self.send(message, authenticate=False)

    async def ping(self):
        # Doesn't require admin secret
        message = {"janus": "ping"}
        return await self.send(message, authenticate=False)

    async def add_token(self, token: str = uuid.uuid4().hex, plugins: list = []):
        payload: dict = {"janus": "add_token", "token": token}
        if plugins:
            payload["plugins"] = plugins
        return await self.send(payload)

    async def allow_token(self, token: str, plugins: list):
        # if not plugins:
        #     raise Exception("plugins should be non-empty array")
        payload = {
            "janus": "allow_token",
            "token": token,
            "plugins": plugins,
        }
        return await self.send(payload)

    async def disallow_token(self, token: str, plugins: list):
        # if not plugins:
        #     raise Exception("plugins should be non-empty array")
        payload = {
            "janus": "disallow_token",
            "token": token,
            "plugins": plugins,
        }
        return await self.send(payload)

    async def list_tokens(self):
        payload = {"janus": "list_tokens"}
        result = await self.send(payload)
        return result["data"]["tokens"]

    async def remove_token(self, token: str):
        payload = {
            "janus": "remove_token",
            "token": token,
        }
        return await self.send(payload)
