# Experiments

This is a place for rapid prototyping, ensuring production quality of code while avoiding Git process overhead.

## FFmpeg

The VideoRoom plugin implemented in [plugin_video_room_ffmpeg.py](./janus_client/plugin_video_room_ffmpeg.py) uses FFmpeg. It depends on the ffmpeg-cli, and that is required to be installed separately.

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

## Support for GStreamer VideoRoom plugin has been deprecated since v0.2.5

Contributions to migrate the [plugin](./janus_client/plugin_video_room.py) to latest `JanusPlugin` API would be greatly appreciated.
