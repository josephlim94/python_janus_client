
from janus_client_py import JanusPlugin

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

    async def join(self, room_id, publisher_id, display_name):
        def complete_condition(response):
            if response["janus"] == "event":
                return True
            else:
                return False
        await self.send({
            "janus": "message",
            "body": {
                "request": "join",
                "ptype" : "publisher",
                "room": room_id,
                "id": publisher_id,
                "display": display_name,
            }
        }, complete_condition=complete_condition)

    async def subscribe(self, room_id, feed_id):
        def complete_condition(response):
            if response["janus"] == "event":
                return True
            else:
                return False
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
        }, complete_condition=complete_condition)

    async def unsubscribe(self):
        await self.send({
            "janus": "message",
            "body": {
                "request": "leave",
            }
        })

    async def list_participants(self, room_id) -> list:
        response = await self.send({
            "janus": "message",
            "body": {
                "request": "listparticipants",
                "room": room_id,
            }
        })
        return response["plugindata"]["data"]["participants"]