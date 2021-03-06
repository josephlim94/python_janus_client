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

### In Progress

:clock3: Emit events to respective session and plugin handlers  
:clock3: Create plugin for videoroom plugin  

### Dependencies

- [websockets](https://github.com/aaugustin/websockets)

---

## Development

The package hopes to implement a general purpose client that can communicate with a Janus server. Examples like VideoRoom plugin is not part of their core features, so it's not included in the package.  
But it can still be included as a default example though. It's up for discussion. :D The reason stopping me from doing that is because I'm depending on GStreamer to use WebRTC and media streaming, and it's not trivial to install it. Please refer to [Quirks section](#quirks).

You can refer to [video_room_plugin.py](./video_room_plugin.py) to see how a specific plugin handle is implemented.

And in [main.py](./main.py), you will be able to find references on how to use the client in general such as connecting and creating sessions.
Essence:

```python
import asyncio
import ssl
import pathlib
from janus_client import JanusClient, JanusSession
from video_room_plugin import JanusVideoRoomPlugin

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

### Compiling GStreamer

Clone gst-build repo and build it. Warning, I'm in Malaysia and the download speed is very low when cloning projects in meson. One useful practice I learned is to enable VNC server on the RPI, and then use VNC viewer to open desktop and open terminal to start meson build. With this, your build won't stop when you close VNC Viewer so you can let it run overnight. It's better than doing direct SSH, and saves a bit electricity if you have a monitor.  
For advanced users, you can manually change the meson build file to pull from github mirror if the gitlab url is slow for you too.  
[GStreamer mirror](https://github.com/GStreamer)

Below is a summary of commands to build GStreamer, please refer to [Building from source using meson](https://gstreamer.freedesktop.org/documentation/installing/building-from-source-using-meson.html?gi-language=python#building-from-source-using-meson) for more info.

```bash
# Clone build repo from Github mirror
git clone https://github.com/GStreamer/gst-build.git
cd gst-build
# Initialise build
meson build_directory
# Configure build
meson configure -Dpython=enabled -Dgst-plugins-bad:webrtc=enabled -Dgst-plugins-base:opus=enabled -Dgst-plugins-bad:srtp=enabled -Ddoc=disabled build_directory/
# Build and install
ninja -C build_directory/
ninja -C build_directory/ install
```

For reference, here are some extra external libraries I installed for the compilation (far from exhaustive, some might be optional):

```bash
# For hotdoc
apt-get install libxml2-dev libxslt1-dev cmake libyaml-dev libclang-dev llvm-dev libglib2.0-dev libjson-glib-dev
pip3 install hotdoc
# GStreamer
apt-get install libmount-dev flex bison nasm libavfilter-dev gobject-introspection libgirepository1.0-dev libsrtp2-dev libjpeg-dev
#apt-get install libgtk-3-dev libopus-dev alsa-tools alsa-utils libogg-dev
```

Test your installation by running "webrtc/janus/janusvideoroom.py" from [gst-examples repo](https://gitlab.freedesktop.org/gstreamer/gst-examples/).

### Raspbian Stretch GStreamer

In case you are wondering about other versions of Raspbian, I've tested with Raspbian Stretch.  
The Gstreamer version distributed with it is v1.10.1, and webrtcbin is first introduced in v1.13.1, referencing [here](https://github.com/GStreamer/gst-plugins-bad/commit/1894293d6378c69548d974d2965e9decc1527654#diff-ebe724724a159c2186ae82d0adc58e960af844c0e472d37e5361ff9d157811a9).  
So, still need to recompile GStreamer.
