
from janus_client import JanusPlugin
import asyncio

import gi
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gst
gi.require_version('GstWebRTC', '1.0')
from gi.repository import GstWebRTC
gi.require_version('GstSdp', '1.0')
from gi.repository import GstSdp

class JanusVideoRoomPlugin(JanusPlugin):
    name = "janus.plugin.videoroom"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.joined_event = asyncio.Event()

    def handle_async_response(self, response):
        if response["janus"] == "event":
            if "plugindata" in response:
                if response["plugindata"]["data"]["videoroom"] == "attached":
                    self.joined_event.set()
        else:
            print("Unimplemented response handle:", response["janus"])
            print(response)
        # Handle JSEP
        if "jsep" in response:
            print("Got JSEP:", response["jsep"])

    async def join(self, room_id, publisher_id, display_name):
        await self.send({
            "janus": "message",
            "body": {
                "request": "join",
                "ptype" : "publisher",
                "room": room_id,
                "id": publisher_id,
                "display": display_name,
            }
        })
        await self.joined_event.wait()

    async def subscribe(self, room_id, feed_id):
        await self.send({
            "janus": "message",
            "body": {
                "request": "join",
                "ptype" : "subscriber",
                "room": room_id,
                "feed": feed_id,
                # "close_pc": True,
                # "audio": True,
                # "video": True,
                # "data": True,
                # "offer_audio": True,
                # "offer_video": True,
                # "offer_data": True,
            }
        })
        await self.joined_event.wait()

    async def unsubscribe(self):
        await self.send({
            "janus": "message",
            "body": {
                "request": "leave",
            }
        })
        self.joined_event.clear()

    async def list_participants(self, room_id) -> list:
        response = await self.send({
            "janus": "message",
            "body": {
                "request": "listparticipants",
                "room": room_id,
            }
        })
        return response["plugindata"]["data"]["participants"]