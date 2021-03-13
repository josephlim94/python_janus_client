# Janus Client for Python

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) ![Development Stage](https://img.shields.io/badge/Stage-ALPHA-orange.svg)

This is a [Janus](https://github.com/meetecho/janus-gateway) webrtc client written in Python, to be used with asyncio.

---

## Installing

```bash
pip install janus-client
```

---

## Description

### Features

:heavy_check_mark: Connect to Janus server through websocket (using [websockets](https://github.com/aaugustin/websockets))  
:heavy_check_mark: Handle transactions with Janus  
:heavy_check_mark: Create/destroy sessions  
:heavy_check_mark: Create/destroy plugins  
:heavy_check_mark: Handle multiple sessions and or multiple plugins at the same time  
:heavy_check_mark: Support authentication with shared static secret (API key) and/or stored token  
:heavy_check_mark: Expose Admin/Monitor API client  

### In Progress

:clock3: Emit events to respective session and plugin handlers  
:clock3: Create plugin for videoroom plugin  

### Dependencies

- [websockets](https://github.com/aaugustin/websockets)

---

## Development

The package is implementing a general purpose client that can communicate with a Janus server.

Examples like VideoRoom plugin are also included in the package, but currently it depends on GStreamer for WebRTC and media streaming, and it will not be automatically installed. The reason for this is because it's not trivial to install/recompile it. Please refer to [Quirks section](#quirks).

You can refer to [video_room_plugin.py](./video_room_plugin.py) to see how a specific plugin handle is implemented.

And in [main.py](./main.py), you will be able to find references on how to use the client in general, such as connecting and creating sessions.

Essence:

```python
import asyncio
import ssl
import pathlib
from janus_client import JanusClient, JanusSession, JanusVideoRoomPlugin

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
localhost_pem = pathlib.Path(__file__).with_name("lt_limmengkiat_name_my.crt")
ssl_context.load_verify_locations(localhost_pem)

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
        # WebRTC streaming not implemented  for subscriber yet
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

### Quirks

On my RPI 2 Raspbian Buster, there's a problem with GStreamer installed from distribution repository.
It's complaining about ssl and then failing DTLS.  
Referring to this PR: [webrtcbin: fix DTLS when receivebin is set to DROP](https://gitlab.freedesktop.org/gstreamer/gst-plugins-bad/-/merge_requests/407)  
I believe there is a bug in the distributed GStreamer version (v1.14.4) thus I recompiled it on my RPI 2  
There's also a chance that it's a problem with openssl itself, an incompatibility.
Refering to this gist: [OpenSSL DTLS problem in Debian buster](https://gist.github.com/feymartynov/fdfa1a9691d77f2ef9bd7468ba9b8710)

Because of these, please recompile GStreamer with version above 1.14.4.

If recompiling GStreamer on RPI, there's this issue: [rpicamsrc 1.18.3 failed](https://gitlab.freedesktop.org/gstreamer/gst-plugins-good/-/issues/839).  
You can patch the build with this PR: [rpicamsrc: depend on posix threads and vchiq_arm](https://gitlab.freedesktop.org/gstreamer/gst-plugins-good/-/merge_requests/875/diffs) or build with master branch.

And then another quirk, the example was still unable to setup a peer connection to my janus server at lt.limmengkiat.name.my. I had to enable ice_tcp (ice_tcp=true) in janus.jcfg for it to work. I don't know why yet.  
![Janus Enable ICE TCP](janus_enable_ice_tcp.png "Janus Enable ICE TCP")

### Recompiling GStreamer

Please refer to our Wiki page: [Compiling GStreamer](https://github.com/josephlim94/janus_gst_client_py/wiki/Compile-GStreamer)
