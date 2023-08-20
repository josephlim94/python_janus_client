# Python Janus Client

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) ![Development Stage](https://img.shields.io/badge/Stage-ALPHA-orange.svg) [![Documentation Status](https://readthedocs.org/projects/janus-client-in-python/badge/?version=latest)](https://janus-client-in-python.readthedocs.io/en/latest/?badge=latest) ![UT Coverage](https://img.shields.io/badge/coverage-80%25-green)


[Janus](https://github.com/meetecho/janus-gateway) WebRTC gateway Python async client.

---

## Install

```bash
pip install janus-client
```

---

## Description

This Python client communicates with Janus WebRTC server to use provided services. It's using `aiortc` for WebRTC communication and subsequently `PyAV` for media stack.

FFmpeg support for VideoRoom plugin has now been moved to `experiments` folder, together with GStreamer support.

## Goals

- Simple interface
- Minimal dependency/Maximum compatibility
- Extendable

## Features

:heavy_check_mark: Connect to Janus server through:
  - Websocket API ([websockets](https://github.com/aaugustin/websockets))
  - HTTP ([aiohttp](https://docs.aiohttp.org/en/stable/index.html))

:heavy_check_mark: Manage Janus client connection, session, and plugins  
:heavy_check_mark: Multiple connections in parallel  
:heavy_check_mark: Direct message transactions to correct senders asynchronously  
```python
from janus_client import JanusSession, JanusEchoTestPlugin, JanusVideoRoomPlugin

# Protocol will be derived from base_url
session = JanusSession(
    base_url="wss://janusmy.josephgetmyip.com/janusbasews/janus",
)
# OR
session = JanusSession(
    base_url="https://janusmy.josephgetmyip.com/janusbase/janus",
)

plugin_handle_1 = JanusVideoRoomPlugin()
plugin_handle_2 = JanusEchoTestPlugin()

# Attach to Janus session
await plugin_handle_1.attach(session=session)
await plugin_handle_2.attach(session=session)

# Destroy plugin handles in parallel
await asyncio.gather(
    plugin_handle_1.destroy(), plugin_handle_2.destroy()
)
```
:heavy_check_mark: Support authentication with shared static secret (API key) and/or stored token  
:heavy_check_mark: Expose Admin/Monitor API client  
:heavy_check_mark: Janus VideoRoom plugin with FFmpeg (Partial: Only sends video)  
```python
from janus_client import JanusVideoRoomPlugin
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

plugin_handle_1 = JanusVideoRoomPlugin()
await plugin_handle_1.join(room_id, publisher_id, display_name)
await plugin_handle_1.publish(ffmpeg_input=ffmpeg_input, width=width, height=height)
await asyncio.sleep(60)
await plugin_handle_1.unpublish()
```
:heavy_check_mark: Janus EchoTest plugin  
```python
from janus_client import JanusEchoTestPlugin

plugin_handle_2 = JanusEchoTestPlugin()
await plugin_handle_2.start(
    play_from="./Into.the.Wild.2007.mp4", record_to="./asdasd.mp4"
)
await asyncio.sleep(15)
await plugin_handle_2.close_stream()
```
:heavy_check_mark: Janus VideoCall plugin (Please refer to [eg_videocall_in.py](./eg_videocall_in.py) and [eg_videocall_out.py](./eg_videocall_out.py))  

---

## Examples

## Demo

Use [test_ffmpeg.py](./test_ffmpeg.py) to try streaming a portion of monitor display to Janus videoroom demo.

Result:

Delay of 0.175s

![image](https://github.com/josephlim94/janus_gst_client_py/assets/5723232/739ba55a-71b9-445a-b823-a09a72ae9fb5)

Server ping:

![image](https://github.com/josephlim94/janus_gst_client_py/assets/5723232/e08c3f2d-d12e-4aa3-8c81-3539be4b0304)

## Documentation

:construction: Under construction :construction:
