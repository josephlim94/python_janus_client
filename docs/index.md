# Python Janus Client

Easily send and share WebRTC media through [Janus](https://github.com/meetecho/janus-gateway) WebRTC server.

## Key Features

- Supports HTTP/s and WebSockets communication with Janus.
- Support Admin/Monitor API:
    - Generic requests
    - Configuration related requests
    - Token related requests
- Supports Janus plugin:
    - EchoTest Plugin
    - VideoCall Plugin
    - VideoRoom Plugin
    - TextRoom Plugin
- Extendable Transport class and Plugin class

## Library Installation

```bash
pip install janus-client
```

## Getting Started

### Simple Connect And Disconnect

```python
import asyncio
from janus_client import JanusSession, JanusEchoTestPlugin, JanusVideoRoomPlugin

# Protocol will be derived from base_url
base_url = "wss://janusmy.josephgetmyip.com/janusbasews/janus"
# OR
base_url = "https://janusmy.josephgetmyip.com/janusbase/janus"

session = JanusSession(base_url=base_url)

plugin_handle = JanusEchoTestPlugin()

# Attach to Janus session
await plugin_handle.attach(session=session)

# Destroy plugin handle
await plugin_handle.destroy()
```

This will create a plugin handle and then destroy it.

Notice that we don't need to call connect or disconnect explicitly. It's managed internally.

### Make Video Calls (Outgoing)

```python
import asyncio
from janus_client import JanusSession, JanusVideoCallPlugin
from aiortc.contrib.media import MediaPlayer, MediaRecorder
from aiortc import RTCConfiguration, RTCIceServer

async def main():
    # Create session
    session = JanusSession(
        base_url="wss://janusmy.josephgetmyip.com/janusbasews/janus",
    )

    # Create plugin (optionally with WebRTC configuration)
    config = RTCConfiguration(iceServers=[
        RTCIceServer(urls='stun:stun.l.google.com:19302')
    ])
    plugin_handle = JanusVideoCallPlugin(pc_config=config)

    # Attach to Janus session
    await plugin_handle.attach(session=session)

    # Prepare username and media stream
    username = "testusernamein"
    username_out = "testusernameout"

    player = MediaPlayer(
        "desktop",
        format="gdigrab",
        options={
            "video_size": "640x480",
            "framerate": "30",
            "offset_x": "20",
            "offset_y": "30",
        },
    )
    recorder = MediaRecorder("./videocall_record_out.mp4")

    # Register myself as testusernameout
    result = await plugin_handle.register(username=username_out)

    # Call testusernamein
    result = await plugin_handle.call(
        username=username, player=player, recorder=recorder
    )

    # Wait awhile then hangup
    await asyncio.sleep(30)

    result = await plugin_handle.hangup()

    # Destroy plugin
    await plugin_handle.destroy()

    # Destroy session
    await session.destroy()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
```

This example will register to the VideoCall plugin using username `testusernameout`. It will then call the user registered using the username `testusernamein`.

A portion of the screen will be captured and sent in the call media stream.
The incoming media stream will be saved into `videocall_record_out.mp4` file.

### Receive Video Calls (Incoming)

```python
import asyncio
from janus_client import JanusSession, JanusVideoCallPlugin, VideoCallEventType
from aiortc.contrib.media import MediaPlayer, MediaRecorder

async def main():
    # Create session
    session = JanusSession(
        base_url="wss://janusmy.josephgetmyip.com/janusbasews/janus",
    )

    # Create plugin
    plugin_handle = JanusVideoCallPlugin()

    # Attach to Janus session
    await plugin_handle.attach(session=session)

    # Register username
    username = "testusernamein"
    await plugin_handle.register(username=username)

    # Set up event handler for incoming calls
    async def on_incoming_call(data):
        print(f"Incoming call from {data['username']}")
        
        # Get JSEP from event data
        jsep = data['jsep']
        
        # Set up media
        player = MediaPlayer("input.mp4")
        recorder = MediaRecorder("./videocall_record_in.mp4")
        
        # Accept the call with JSEP
        await plugin_handle.accept(jsep, player, recorder)
        print("Call accepted")

    # Register the event handler
    plugin_handle.on_event(VideoCallEventType.INCOMINGCALL, on_incoming_call)

    # Wait for incoming calls
    print(f"Waiting for calls as '{username}'...")
    await asyncio.sleep(60)

    # Cleanup
    await plugin_handle.destroy()
    await session.destroy()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
```

This example demonstrates the event-driven API for handling incoming calls. The plugin uses callbacks to notify you of incoming calls, and you can accept them by calling `accept()` with the JSEP data from the event.
