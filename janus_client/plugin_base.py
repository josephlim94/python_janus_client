
import asyncio
from .session import JanusSession

class JanusPlugin():
    name = "janus.plugin.base.dummy"

    def __init__(self, session: JanusSession, handle_id: str):
        self.session = session
        self.id = handle_id

    async def destroy(self):
        message = {
            "janus": "detach",
        }
        await self.send(message)
        self.session.destroy_plugin_handle(self)

    async def send(self, message, **kwargs):
        if "handle_id" in message:
            raise Exception("Handle ID in message must not be manually added")
        message["handle_id"] = self.id
        return await self.session.send(message, **kwargs)

    def handle_async_response(self, response: dict):
        # This is response for self
        raise NotImplementedError()

    async def trickle(self, sdpMLineIndex, candidate):
        candidate_payload = dict()
        if candidate:
            candidate_payload = {
                "sdpMLineIndex" : sdpMLineIndex,
                "candidate" : candidate,
            }
        else:
            # Reference: https://janus.conf.meetecho.com/docs/rest.html
            # - a null candidate or a completed JSON object to notify the end of the candidates.
            # TODO: test it
            candidate_payload = None
        await self.send({
            "janus": "trickle",
            "candidate": candidate_payload
        })
        # TODO: Implement sending an array of candidates