# import asyncio
import logging

from .plugin_base import JanusPlugin

logger = logging.getLogger(__name__)


class JanusEchoTestPlugin(JanusPlugin):
    """Janus EchoTest plugin implementation"""

    name = "janus.plugin.echotest"
