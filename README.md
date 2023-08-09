# Janus Client in Python

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) ![Development Stage](https://img.shields.io/badge/Stage-ALPHA-orange.svg) [![Documentation Status](https://readthedocs.org/projects/janus-client-in-python/badge/?version=latest)](https://janus-client-in-python.readthedocs.io/en/latest/?badge=latest) ![UT Coverage](https://img.shields.io/badge/coverage-71%25-orange)


A [Janus](https://github.com/meetecho/janus-gateway) WebRTC client in Python asyncio.

---

## Install

```bash
pip install janus-client
```

---

## Description

This is a client that can communicate with Janus WebRTC server to use provided services.

The VideoRoom plugin implemented in [plugin_video_room_ffmpeg.py](./janus_client/plugin_video_room_ffmpeg.py) uses FFmpeg. It depends on the ffmpeg-cli, and that is required to be installed separately.

### Features

:heavy_check_mark: Connect to Janus server through:
  - Websocket API ([websockets](https://github.com/aaugustin/websockets))
  - HTTP ([aiohttp](https://docs.aiohttp.org/en/stable/index.html))

:heavy_check_mark: Automatically manage Janus client connection  
:heavy_check_mark: Manage message transactions with Janus  
:heavy_check_mark: Manage sessions  
```python
from janus_client import JanusSession

# Protocol will be derived from base_url
session = JanusSession(
    base_url="wss://janusmy.josephgetmyip.com/janusbasews/janus",
)
# OR
session = JanusSession(
    base_url="https://janusmy.josephgetmyip.com/janusbase/janus",
)
```
:heavy_check_mark: Manage plugins  
:heavy_check_mark: Manage multiple sessions and or multiple plugins at the same time  
```python
from janus_client import JanusVideoRoomPlugin

plugin_handle_1 = JanusVideoRoomPlugin()
plugin_handle_2 = JanusVideoRoomPlugin()

# Attach to Janus session
await plugin_handle_1.attach(session=session)
await plugin_handle_2.attach(session=session)
```
:heavy_check_mark: Support authentication with shared static secret (API key) and/or stored token  
:heavy_check_mark: Expose Admin/Monitor API client  
:heavy_check_mark: Use Janus VideoRoom plugin with FFmpeg  
```python
import ffmpeg

room_id = 1234
publisher_id = 333
display_name = "qweqwe"

width = 640
height = 480
ffmpeg_input = ffmpeg.input(
    "desktop",
    format="gdigrab",
    framerate=30,
    offset_x=20,
    offset_y=30,
    video_size=[
        width,
        height,
    ],
    show_region=1,
)

await plugin_handle_1.join(room_id, publisher_id, display_name)
await plugin_handle_1.publish(ffmpeg_input=ffmpeg_input, width=width, height=height)
await asyncio.sleep(60)
await plugin_handle_1.unpublish()
```

### FFmpeg Stream To WebRTC (:warning: **WARNING !!!**)

This FFmpeg stream to WebRTC solution is a hack. The fact is that FFmpeg doesn't support WebRTC and aiortc is implemented using PyAV. PyAV has much less features than a full fledged installed FFmpeg, so to support more features and keep things simple, I hacked about a solution without the use of neither WHIP server nor UDP nor RTMP.

First the ffmpeg input part should be constructed by the user, before passing it to `JanusVideoRoomPlugin.publish`. When the media player needs to stream the video, the following happens:
1. A thread will be created and a ffmpeg process will be created. Output of ffmpeg is hardcoded to be `rawvideo rgb24`.
2. Thread reads output of ffmpeg process.
3. Coverts the output data to numpy array and then to `av.VideoFrame` frame.
4. Hack the `pts` and `time_base` parameter of the frame. I don't know what it is and just found a value that works.
5. Put the frame into video track queue to be received and sent by `aiortc.mediastreams.MediaStreamTrack`.

References:
- [Aiortc Janus](https://github.com/aiortc/aiortc/tree/main/examples/janus).
- [FFmpeg webrtc](https://github.com/ossrs/ffmpeg-webrtc/pull/1).

### TODO

:clock3: Publish audio with FFmpeg VideoRoom plugin  
:clock3: Subscribe to stream with FFmpeg VideoRoom plugin  
:clock3: Disable keepalive recurring task for HTTP transport  
:clock3: Handle error when fail to join room because of "User ID _ already exists" error  

---

## Usage

Use [test_ffmpeg.py](./test_ffmpeg.py) to try streaming a portion of monitor display to Janus videoroom demo.

Result:

Delay of 0.175s

![image](https://github.com/josephlim94/janus_gst_client_py/assets/5723232/739ba55a-71b9-445a-b823-a09a72ae9fb5)

Server ping:

![image](https://github.com/josephlim94/janus_gst_client_py/assets/5723232/e08c3f2d-d12e-4aa3-8c81-3539be4b0304)

### Support for GStreamer VideoRoom plugin has been deprecated since v0.2.5

Contributions to migrate the [plugin](./janus_client/plugin_video_room.py) to latest `JanusPlugin` API would be greatly appreciated.

## Documentation

:construction: Under construction :construction:
