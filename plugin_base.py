
import asyncio
from session import JanusSession

class JanusPlugin():
    name = "janus.plugin.base.dummy"

    def __init__(self, session: JanusSession, handle_id: str):
        self.session = session
        self.handle_id = handle_id

    async def send(self, message, **kwargs):
        if "handle_id" in message:
            raise Exception("Handle ID in message must not be manually added")
        message["handle_id"] = self.handle_id
        return await self.session.send(message, **kwargs)

    async def destroy(self):
        message = {
            "janus": "detach",
        }
        await self.send(message)

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

    async def unsubscribe(self):
        await self.send({
            "janus": "message",
            "body": {
                "request": "leave",
            }
        })