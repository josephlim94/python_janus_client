import asyncio
import json
import uuid
from typing import Dict, Any
import logging

import websockets
from .transport import JanusTransport
from .transport_http import JanusTransportHTTP


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
    transport: JanusTransport
    admin_secret: str

    def __init__(
        self,
        base_url: str,
        admin_secret: str,
        api_secret: str = None,
        token: str = None,
    ):
        self.transport = JanusTransport.create_transport(
            base_url=base_url,
            api_secret=api_secret,
            token=token,
        )
        self.admin_secret = admin_secret

    def __str__(self):
        return f"Admin/Monitor ({self.transport.base_url}) {self}"

    async def connect(self) -> None:
        """Initialize resources"""
        await self.transport.connect()

    async def disconnect(self) -> None:
        """Release resources"""
        await self.transport.disconnect()

    async def info(self) -> Dict:
        """Get server info. Gets the same info as transport info API."""
        if isinstance(self.transport, JanusTransportHTTP):
            return await self.transport.info()
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
