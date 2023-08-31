import uuid
from typing import Dict, Union, List
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

When it comes to authentication:
- If stored-token auth (token) is enabled, all requests will require auth.
  At this point, the token can only be created through admin add token API.
- Admin API uses it's own auth method (admin_secret)
- If shared static token auth (api_secret) is enabled, all requests can choose to use this
  auth instead of token auth.
"""


class JanusAdminMonitorClient:
    """
    An Admin/Monitor API that can be used to ask Janus for more specific information related to sessions and handles.
    """

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

    async def set_session_timeout(self, session_timeout: int) -> int:
        """
        Change global session timeout value in Janus.
        Returns the value that it is set to.
        """

        response = await self.send_wrapper(
            message={"janus": "set_session_timeout", "timeout": session_timeout},
            matcher={"janus": "success", "timeout": None},
        )
        return response["timeout"]

    async def set_log_level(self, log_level: int) -> int:
        """
        Change the log level in Janus.
        Returns the value that it is set to.
        """

        response = await self.send_wrapper(
            message={"janus": "set_log_level", "level": log_level},
            matcher={"janus": "success", "level": None},
        )
        return response["level"]

    async def set_log_timestamps(self, log_timestamps: bool) -> bool:
        """
        Selectively enable/disable adding a timestamp to all log lines
        Janus writes on the console and/or to file.
        Returns the value that it is set to.
        """

        response = await self.send_wrapper(
            message={"janus": "set_log_timestamps", "timestamps": log_timestamps},
            matcher={"janus": "success", "log_timestamps": None},
        )
        return response["log_timestamps"]

    async def set_log_colors(self, log_colors: bool) -> bool:
        """
        Selectively enable/disable using colors in all log lines
        Janus writes on the console and/or to file.
        Returns the value that it is set to.
        """

        response = await self.send_wrapper(
            message={"janus": "set_log_colors", "colors": log_colors},
            matcher={"janus": "success", "log_colors": None},
        )
        return response["log_colors"]

    async def set_locking_debug(self, locking_debug: bool) -> bool:
        """
        Selectively enable/disable a live debugging of the locks in
        Janus on the fly (useful if you're experiencing deadlocks
        and want to investigate them).
        Returns the value that it is set to.
        """

        response = await self.send_wrapper(
            message={"janus": "set_locking_debug", "debug": locking_debug},
            matcher={"janus": "success", "locking_debug": None},
        )
        return response["locking_debug"]

    async def set_refcount_debug(self, refcount_debug: bool) -> bool:
        """
        Selectively enable/disable a live debugging of the reference
        counters in Janus on the fly (useful if you're experiencing
        memory leaks in the Janus structures and want to investigate them).
        Returns the value that it is set to.
        """

        response = await self.send_wrapper(
            message={"janus": "set_refcount_debug", "debug": refcount_debug},
            matcher={"janus": "success", "refcount_debug": None},
        )
        return response["refcount_debug"]

    async def set_libnice_debug(self, libnice_debug: bool) -> bool:
        """
        Selectively enable/disable libnice debugging.
        Returns the value that it is set to.
        """

        response = await self.send_wrapper(
            message={"janus": "set_libnice_debug", "debug": libnice_debug},
            matcher={"janus": "success", "libnice_debug": None},
        )
        return response["libnice_debug"]

    async def set_min_nack_queue(self, min_nack_queue: int) -> int:
        """
        Change the value of the min NACK queue window.
        Returns the value that it is set to.
        """

        response = await self.send_wrapper(
            message={"janus": "set_min_nack_queue", "min_nack_queue": min_nack_queue},
            matcher={"janus": "success", "min_nack_queue": None},
        )
        return response["min_nack_queue"]

    async def set_no_media_timer(self, no_media_timer: int) -> int:
        """
        Change the value of the no-media timer property.
        Returns the value that it is set to.
        """

        response = await self.send_wrapper(
            message={"janus": "set_no_media_timer", "no_media_timer": no_media_timer},
            matcher={"janus": "success", "no_media_timer": None},
        )
        return response["no_media_timer"]

    async def set_slowlink_threshold(self, slowlink_threshold: int) -> int:
        """
        Change the value of the slowlink-threshold property.
        Returns the value that it is set to.
        """

        response = await self.send_wrapper(
            message={
                "janus": "set_slowlink_threshold",
                "slowlink_threshold": slowlink_threshold,
            },
            matcher={"janus": "success", "slowlink_threshold": None},
        )
        return response["slowlink_threshold"]

    # Token related requests

    async def list_tokens(self) -> List:
        """
        List the existing tokens
        (only available if you enabled the Stored token based authentication mechanism);
        """

        response = await self.send_wrapper(
            message={"janus": "list_tokens"},
            matcher={"janus": "success", "data": {"tokens": None}},
        )
        return response["data"]["tokens"]

    async def add_token(self, token: str = uuid.uuid4().hex, plugins: list = []) -> str:
        """
        Add a valid token
        (only available if you enabled the Stored token based authentication mechanism)

        Ok to add the same token repeatedly.
        Plugin permissions provided in input will be added to existing permissions.
        Providing empty plugin permissions will allow access to all plugins.
        """

        success_matcher = {"janus": "success", "data": {"plugins": None}}
        response = await self.send_wrapper(
            message={
                "janus": "add_token",
                "token": token,
                "plugins": plugins,
            },
            matcher=success_matcher,
        )

        if not is_subset(response, success_matcher):
            raise Exception("Fail to add token")

        return token

    async def remove_token(self, token: str) -> bool:
        """
        Remove a token
        (only available if you enabled the Stored token based authentication mechanism)

        Will fail if the token is not already added.
        """

        success_matcher = {"janus": "success"}
        response = await self.send_wrapper(
            message={
                "janus": "remove_token",
                "token": token,
            },
            matcher=success_matcher,
        )

        if not is_subset(response, success_matcher):
            raise Exception("Fail to remove token")

        return True

    async def allow_token(self, token: str, plugins: list) -> List:
        """
        Give a token access to a plugin
        (only available if you enabled the Stored token based authentication mechanism)

        Ok to allow the same token permissions repeatedly.
        Plugin permissions provided in input will be added to existing permissions.
        Empty permission list is not accepted.
        Invalid plugin permissions are not accepted.
        """

        if not plugins:
            raise Exception("plugins should be non-empty array")

        success_matcher = {"janus": "success", "data": {"plugins": None}}
        response = await self.send_wrapper(
            message={
                "janus": "allow_token",
                "token": token,
                "plugins": plugins,
            },
            matcher=success_matcher,
        )

        if not is_subset(response, success_matcher):
            raise Exception("Fail to allow token")

        return response["data"]["plugins"]

    async def disallow_token(self, token: str, plugins: list):
        """
        Remove a token access from a plugin
        (only available if you enabled the Stored token based authentication mechanism)

        Ok to disallow the same token permissions repeatedly.
        Plugin permissions provided in input will be removed from existing permissions.
        Empty permission list is not accepted.
        Invalid plugin permissions are not accepted.
        """

        if not plugins:
            raise Exception("plugins should be non-empty array")

        success_matcher = {"janus": "success", "data": {"plugins": None}}
        response = await self.send_wrapper(
            message={
                "janus": "disallow_token",
                "token": token,
                "plugins": plugins,
            },
            matcher=success_matcher,
        )

        if not is_subset(response, success_matcher):
            raise Exception("Fail to disallow token")

        return response["data"]["plugins"]
