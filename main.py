
import ssl
import asyncio
import websockets
import json

# ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
# ssl_context.check_hostname = False
# ssl_context.verify_mode = ssl.CERT_NONE

class JanusClient:
    def __init__(self, uri: str = ""):
        self.uri = uri

    async def connect(self) -> None:
        print("Connecting to: ", self.uri)
        # self.ws = await websockets.connect(self.uri, ssl=ssl_context)
        self.ws = await websockets.connect(self.uri, subprotocols=["janus-protocol"])
        print("Connected")

    async def disconnect(self):
        print("Disconnecting")
        await self.ws.close()

async def main():
    client = JanusClient("ws://lt.limmengkiat.name.my/janusws/")
    await client.connect()
    # Create session
    await client.ws.send(json.dumps({
        "janus": "create",
        "transaction": "1234"
    }))
    response = json.loads(await client.ws.recv())
    print(response)
    if response["janus"] == "success":
        # Session created
        # Attach plugin
        await client.ws.send(json.dumps({
            "janus": "attach",
            "transaction": "1235",
            "session_id": response["data"]["id"],
            "plugin": "janus.plugin.echotest",
        }))
        response_plugin = json.loads(await client.ws.recv())
        print(response_plugin)
        if response_plugin["janus"] == "success":
            # Plugin attached
            # Destroy plugin
            await client.ws.send(json.dumps({
                "janus": "detach",
                "transaction": "1236",
                "session_id": response["data"]["id"],
                "handle_id": response_plugin["data"]["id"],
            }))
            print(await client.ws.recv())
            print(await client.ws.recv())
        # Destroy session
        await client.ws.send(json.dumps({
            "janus": "destroy",
            "transaction": "1237",
            "session_id": response["data"]["id"],
        }))
        print(await client.ws.recv())
    await client.disconnect()
    print("End of main")

asyncio.run(main())