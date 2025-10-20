import asyncio
import logging

from aiortc.rtcdatachannel import RTCDataChannel
from aiortc.sdp import candidate_from_sdp
from aiortc import RTCPeerConnection, RTCSessionDescription

from janus_client import (
    JanusSession,
    JanusPlugin,
)
from janus_client.message_transaction import is_subset

logger = logging.getLogger(__name__)


class JanusTextRoomPlugin(JanusPlugin):
    """Janus TextRoom plugin implementation"""

    name = "janus.plugin.textroom"
    data_channel: RTCDataChannel

    async def on_receive(self, response: dict):
        print(f"Received message: {response}")

        if "janus" not in response:
            print("Unexpected response")

        if is_subset(response, {"janus": "trickle", "candidate": None}):
            candidate_data = response["candidate"]

            if is_subset(candidate_data, {"completed": True}):
                # await self._pc.addIceCandidate()
                print("Trickle done")
                return

            if not is_subset(
                candidate_data, {"sdpMLineIndex": None, "candidate": None}
            ):
                raise Exception("Invalid candidate data")

            print(self._pc.iceConnectionState)
            print(self._pc.iceGatheringState)

            iceCandidate = candidate_from_sdp(
                response["candidate"]["candidate"].split(":", 1)[1]
            )
            iceCandidate.sdpMid = str(response["candidate"]["sdpMLineIndex"])
            print(iceCandidate)

            await self._pc.addIceCandidate(iceCandidate)

    async def send_wrapper(self, message: dict, matcher: dict) -> dict:
        def function_matcher(response: dict):
            return (
                is_subset(
                    response,
                    {
                        "janus": "success",
                        "plugindata": {
                            "plugin": self.name,
                            "data": matcher,
                        },
                    },
                )
                or is_subset(
                    response,
                    {
                        "janus": "success",
                        "plugindata": {
                            "plugin": self.name,
                            "data": {
                                "textroom": "event",
                            },
                        },
                    },
                )
                or is_subset(response, {"janus": "error", "error": {}})
            )

        message_transaction = await self.send(
            message={
                "janus": "message",
                "body": message,
            },
        )
        message_response = await message_transaction.get(
            matcher=function_matcher, timeout=15
        )
        await message_transaction.done()

        if is_subset(message_response, {"janus": "error", "error": {}}):
            raise Exception(f"Janus error: {message_response}")

    async def list(
        self,
    ) -> dict:
        """List available rooms."""

        return await self.send_wrapper(
            message={
                "request": "list",
            },
            matcher={
                "textroom": "success",
                "list": [],
            },
        )

    async def get_participants_list(self, room: int):
        """List participants in a specific room"""

        return await self.send_wrapper(
            message={
                "request": "listparticipants",
                "room": room,
            },
            matcher={
                "room": room,
                "participants": [],
            },
        )

    async def join_room(self, room: int):
        return await self.send_wrapper(
            message={
                "request": "list",
                "textroom": "join",
                "username": "test_username",
                "room": room,
            },
            matcher={
                "textroom": "success",
                "participants": [],
            },
        )

    async def message(self, room: int, text: str, ack: bool = True):
        return await self.send_wrapper(
            message={
                "request": "list",
                "textroom": "message",
                "room": room,
                "text": text,
                "ack": ack,
            },
            matcher={
                "textroom": "success",
            },
        )

    async def leave(self, room: int):
        return await self.send_wrapper(
            message={
                "request": "list",
                "textroom": "leave",
                "room": room,
            },
            matcher={
                "textroom": "success",
            },
        )

    async def announcement(self, room: int, text: str) -> dict:
        return await self.send_wrapper(
            message={
                "request": "list",
                "textroom": "announcement",
                "room": room,
                "secret": "adminpwd",
                "text": text,
            },
            matcher={
                "textroom": "success",
            },
        )

    async def setup(self) -> dict:
        def function_matcher(response: dict):
            return is_subset(
                response,
                {
                    "janus": "event",
                    "plugindata": {
                        "plugin": self.name,
                        "data": {
                            "textroom": "event",
                            "result": "ok",
                        },
                    },
                },
            ) or is_subset(response, {"janus": "error", "error": {}})

        message_transaction = await self.send(
            message={
                "janus": "message",
                "body": {
                    "request": "setup",
                },
            },
        )
        message_response = await message_transaction.get(
            matcher=function_matcher, timeout=15
        )
        await message_transaction.done()

        if is_subset(message_response, {"janus": "error", "error": {}}):
            raise Exception(f"Janus error: {message_response}")

        print()
        print("setup_response")
        print(message_response)
        print()

        # We will get jsep offer from Janus after we call setup. Not sure if
        # I should reuse PC, but I think I shouldn't
        self._pc = RTCPeerConnection()

        @self._pc.on("datachannel")
        def on_datachannel(channel):
            print(channel, "-", "created by remote party")
            self.data_channel = channel

            @channel.on("message")
            def on_message(message):
                print(channel, "<", message)

                if isinstance(message, str) and message.startswith("ping"):
                    # reply
                    print(channel, "pong" + message[4:])

        await self._pc.setRemoteDescription(
            RTCSessionDescription(
                sdp=message_response["jsep"]["sdp"],
                type=message_response["jsep"]["type"],
            )
        )
        # self.data_channel = self._pc.createDataChannel("JanusDataChannel")
        print(self._pc.signalingState)
        print(self._pc.connectionState)
        print(self._pc.iceConnectionState)
        print(self._pc.iceGatheringState)

        print("--- Wait for trickle ---")
        await asyncio.sleep(5)
        # for candidate in self.ice_candidates:
        #     print(candidate)
        #     await self._pc.addIceCandidate(candidate=candidate)

        await self._pc.setLocalDescription(await self._pc.createAnswer())
        print(self._pc.signalingState)
        print(self._pc.connectionState)
        print(self._pc.iceConnectionState)
        print(self._pc.iceGatheringState)

        message_transaction = await self.send(
            message={
                "janus": "message",
                "body": {
                    "request": "ack",
                },
                "jsep": {
                    "sdp": self._pc.localDescription.sdp,
                    "trickle": True,
                    "type": self._pc.localDescription.type,
                },
            },
        )
        message_response = await message_transaction.get(
            matcher=function_matcher, timeout=15
        )
        await message_transaction.done()

        return message_response


async def main():
    session = JanusSession(
        base_url="ws://janus.lmkprofile.com:8188",
        api_secret="janusrocks",
    )

    plugin_textroom = JanusTextRoomPlugin()

    await plugin_textroom.attach(session=session),

    response = await plugin_textroom.list()

    response = await plugin_textroom.get_participants_list(1234)

    response = await plugin_textroom.setup()

    response = await plugin_textroom.join_room(1234)

    print("--- Wait for awhile ---")
    print(plugin_textroom._pc.signalingState)
    print(plugin_textroom._pc.connectionState)
    print(plugin_textroom._pc.iceConnectionState)
    print(plugin_textroom._pc.iceGatheringState)
    await asyncio.sleep(30)

    response = await plugin_textroom.message(1234, "test msg")

    response = await plugin_textroom.leave(1234)

    response = await plugin_textroom.announcement(1234, "test announcement")

    print(response)
    print("--- Everything done ---")

    await plugin_textroom.destroy()

    await session.destroy()


asyncio.run(main())