import asyncio
import logging

from .plugin_base import JanusPlugin
from .message_transaction import is_subset

logger = logging.getLogger(__name__)


class JanusVideoCallPlugin(JanusPlugin):
    """Janus Video Call plugin implementation"""

    name = "janus.plugin.videocall"  #: Plugin name

    async def on_receive(self, response: dict):
        if response["janus"] == "event":
            logger.info(f"Event response: {response}")
            if "plugindata" in response:
                if response["plugindata"]["data"]["videocall"] == "event":
                    logger.info(
                        f"Event result: {response['plugindata']['data']['result']}"
                    )
        else:
            logger.info(f"Unimplemented response handle: {response}")

        # Handle JSEP. Could be answer or offer.
        if "jsep" in response:
            asyncio.create_task(self.handle_jsep(response["jsep"]))

    async def send_wrapper(self, message: dict, matcher: dict) -> dict:
        def function_matcher(message: dict):
            return is_subset(message, matcher) or is_subset(
                message,
                {
                    "janus": "event",
                    "plugindata": {
                        "plugin": "janus.plugin.videocall",
                        "data": {
                            "videocall": "event",
                            "error_code": None,
                            "error": None,
                        },
                    },
                },
            )

        message_transaction = await self.send(
            message=message,
        )
        response = await message_transaction.get(matcher=function_matcher)
        await message_transaction.done()

        return response

    async def list(self) -> list:
        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": {
                    "request": "list",
                },
            },
            matcher={
                "janus": "event",
                "plugindata": {
                    "plugin": "janus.plugin.videocall",
                    "data": {"videocall": "event", "result": {"list": None}},
                },
            },
        )

        return response["plugindata"]["data"]["result"]["list"]

    async def register(self, username: str) -> None:
        matcher_success = {
            "janus": "event",
            "plugindata": {
                "plugin": "janus.plugin.videocall",
                "data": {
                    "videocall": "event",
                    "result": {
                        "event": "registered",
                    },
                },
            },
        }
        response = await self.send_wrapper(
            message={
                "janus": "message",
                "body": {
                    "request": "register",
                    "username": username,
                },
            },
            matcher=matcher_success,
        )

        return is_subset(response, matcher_success)
