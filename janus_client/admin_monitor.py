import asyncio
import json
import uuid
from typing import Dict, Any, Union, List
import logging

from .transport import JanusTransport
from .transport_http import JanusTransportHTTP
from .message_transaction import is_subset


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
    __transport: JanusTransport
    __admin_secret: str

    def __init__(
        self,
        base_url: str,
        admin_secret: str,
        api_secret: str = None,
        token: str = None,
    ):
        self.__transport = JanusTransport.create_transport(
            base_url=base_url,
            api_secret=api_secret,
            token=token,
            config={"subprotocol": "janus-admin-protocol"},
        )
        self.__admin_secret = admin_secret

    def __str__(self):
        return f"Admin/Monitor ({self.__transport.base_url}) {self}"

    async def connect(self) -> None:
        """Initialize resources"""
        await self.__transport.connect()

    async def disconnect(self) -> None:
        """Release resources"""
        await self.__transport.disconnect()

    async def send_wrapper(
        self,
        message: dict,
        matcher: dict = {},
        jsep: dict = {},
        timeout: Union[float, None] = 15,
        authorize: bool = True,
    ) -> dict:
        def function_matcher(message: dict):
            return is_subset(message, matcher) or is_subset(
                message,
                {
                    "janus": "error",
                    "error": {
                        "code": None,
                        "reason": None,
                    },
                },
            )

        full_message = message
        if jsep:
            full_message = {**message, "jsep": jsep}

        if authorize:
            full_message["admin_secret"] = self.__admin_secret

        message_transaction = await self.__transport.send(
            message=full_message,
        )
        response = await message_transaction.get(
            matcher=function_matcher,
            timeout=timeout,
        )
        await message_transaction.done()

        return response

    async def ping(self) -> Dict:
        """A simple ping/pong mechanism with server. Doesn't require admin secret."""
        return await self.send_wrapper(
            message={"janus": "ping"},
            matcher={"janus": "pong"},
            authorize=False,
        )

    async def info(self) -> Dict:
        """
        Get server info. Gets the same info as transport info API.
        Doesn't require admin secret.
        """

        if isinstance(self.__transport, JanusTransportHTTP):
            return await self.__transport.info()
        else:
            return await self.send_wrapper(
                message={"janus": "info"},
                matcher={"janus": "server_info"},
                authorize=False,
            )

    async def loops_info(self) -> List:
        """
        Returns a summary of how many handles each static event loop is
        currently responsible for, in case static event loops are
        in use (returns an empty array otherwise).
        """

        response = await self.send_wrapper(
            message={"janus": "loops_info"}, matcher={"janus": "success"}
        )
        return response["loops"]

    # Configuration related requests

    async def get_settings(self) -> Dict:
        """
        Gets the current value for the settings that can be modified at
        runtime via the Admin API.
        """
        response = await self.send_wrapper(
            message={"janus": "get_status"},
            matcher={"janus": "success", "status": {}},
        )
        return response["status"]

    async def set_session_timeout(self, session_timeout: int) -> Dict:
        """
        Change global session timeout value in Janus.
        Returns the value that it is set to.
        """
        response = await self.send_wrapper(
            message={"janus": "set_session_timeout", "timeout": session_timeout},
            matcher={"janus": "success", "timeout": None},
        )
        return response["timeout"]

    async def set_log_level(self, log_level: int) -> Dict:
        """
        Change the log level in Janus.
        Returns the value that it is set to.
        """
        response = await self.send_wrapper(
            message={"janus": "set_log_level", "level": log_level},
            matcher={"janus": "success", "level": None},
        )
        return response["level"]

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
