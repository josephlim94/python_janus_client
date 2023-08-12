import asyncio
import logging

from .plugin_base import JanusPlugin

logger = logging.getLogger(__name__)


class JanusVideoCallPlugin(JanusPlugin):
    """Janus Video Call plugin instance

    Implements API to interact with Video Call plugin.
    """

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
        response = await self.send(
            {
                "janus": "message",
                "body": {
                    "request": "list",
                },
            }
        )
        return response
