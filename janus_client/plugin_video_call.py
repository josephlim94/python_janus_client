import asyncio
import logging

from .plugin_base import JanusPlugin

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

    async def list(self) -> None:
        message_transaction = await self.send(
            message={
                "janus": "message",
                "body": {
                    "request": "list",
                },
            },
        )
        response = await message_transaction.get(
            {
                "janus": "event",
                "plugindata": {
                    "plugin": "janus.plugin.videocall",
                    "data": {"videocall": "event", "result": {"list": None}},
                },
            }
        )
        await message_transaction.done()

        return response["plugindata"]["data"]["result"]["list"]
