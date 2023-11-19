![Python Janus Client](https://svgshare.com/i/zsN.svg "Python Janus Client")


[Janus](https://github.com/meetecho/janus-gateway) WebRTC gateway Python async client.

![PyPI - License](https://img.shields.io/pypi/l/janus-client)
![PyPI - Status](https://img.shields.io/pypi/status/janus-client)
![PyPI - Downloads](https://img.shields.io/pypi/dm/janus-client)
[![Documentation Status](https://readthedocs.org/projects/janus-client-in-python/badge/?version=latest)](https://janus-client-in-python.readthedocs.io/en/latest/?badge=latest)
![Code Coverage](https://img.shields.io/badge/coverage-84%25-brightgreen)

---

## Install

```bash
pip install janus-client
```

Requires Python >=3.7 <3.11
> **_NOTE:_**  MacBook Air M1 macOS Ventura requires Python >=3.8

---

## Description

Easily send and share WebRTC media through Janus WebRTC server.

This client is using `aiortc` for WebRTC communication and subsequently `PyAV` for media stack.

## ✅ Features ✅

- Connect to Janus server using:
  - Websocket
  - HTTP
- Authentication with shared static secret (API key) and/or stored token
- Support Admin/Monitor API:
  - Generic requests
  - Configuration related requests
  - Token related requests
- Support Janus plugins:
  - EchoTest plugin
  - VideoCall plugin (Please refer to [eg_videocall_in.py](./eg_videocall_in.py) and [eg_videocall_out.py](./eg_videocall_out.py))
  - VideoRoom plugin
- Simple interface
- Minimum dependency
- Extendable Janus transport

---

## Examples

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

### Make Video Calls

```python
import asyncio
from janus_client import JanusSession, JanusVideoCallPlugin
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

<!-- ## Demo

Use [test_ffmpeg.py](./test_ffmpeg.py) to try streaming a portion of monitor display to Janus videoroom demo.

Result:

Delay of 0.175s

![image](https://github.com/josephlim94/janus_gst_client_py/assets/5723232/739ba55a-71b9-445a-b823-a09a72ae9fb5)

Server ping:

![image](https://github.com/josephlim94/janus_gst_client_py/assets/5723232/e08c3f2d-d12e-4aa3-8c81-3539be4b0304) -->

## Documentation

https://janus-client-in-python.readthedocs.io/

## Experiments

FFmpeg support for VideoRoom plugin has now been moved to `experiments` folder, together with GStreamer support.
