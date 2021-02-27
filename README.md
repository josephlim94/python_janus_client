# Janus Client for Python

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) ![Development Stage](https://img.shields.io/badge/Stage-PROTOTYPE-orange.svg)

This is a [Janus](https://github.com/meetecho/janus-gateway) webrtc client written in Python, to be used with asyncio.

---

## Description

### Features

:heavy_check_mark: Connect to Janus server through websocket (using [websockets](https://github.com/aaugustin/websockets))  
:heavy_check_mark: Create/destroy sessions  
:heavy_check_mark: Create/destroy plugins  
:heavy_check_mark: Handle transactions with Janus  

### In Progress

:clock3: Emit events to respective session and plugin handlers  
:clock3: Create plugin for videoroom plugin  
:clock3: Distribute as PyPI package  

### Dependencies

- [websockets](https://github.com/aaugustin/websockets)

---

## Development

Currently only a base class to create Janus plugin handler is inteded to be distributed, so the [video_room_plugin.py](./video_room_plugin.py) is not in janus_client_py. From there, you can get a reference of how a plugin handler class can be created.

In [main.py](./main.py), you will be able to find references on how to use the client in general such as connecting and creating sessions.
Essence:

```python
from video_room_plugin import JanusVideoRoomPlugin
from janus_client_py import JanusClient, JanusSession

async def main():
    # Connect to server
    client = JanusClient("wss://lt.limmengkiat.name.my/janusws/")
    await client.connect(ssl=ssl_context)
    # Create session
    session = await client.create_session(JanusSession)
    # Create plugin
    plugin_handle = await session.create_plugin_handle(JanusVideoRoomPlugin)

    participants = await plugin_handle.list_participants(1234)
    if len(participants) > 0:
        # Publishers available
        participants_data_1 = participants[0]
        participant_id = participants_data_1["id"]

        # Subscribe to publisher, will get jsep (sdp offer)
        await plugin_handle.subscribe(1234, participant_id)
        # WebRTC streaming not implemented yet
        await asyncio.sleep(5)
        # Unsubscribe from the publisher
        await plugin_handle.unsubscribe()

    # Destroy plugin
    await plugin_handle.destroy()
    # Destroy session
    await session.destroy()
    # Destroy connection
    await client.disconnect()

asyncio.run(main())
```

### Installing for development

Installing gstreamer  
<https://gstreamer.freedesktop.org/documentation/installing/on-linux.html?gi-language=python>

Installing gst python  
<http://lifestyletransfer.com/how-to-install-gstreamer-python-bindings/>

Installing webrtcbin  
<https://github.com/centricular/gstwebrtc-demos/issues/37>  
(gir1.2-gst-plugins-bad-1.0)

More bad plugins  
frei0r-plugins
