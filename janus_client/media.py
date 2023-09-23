import threading
import logging
import errno
import time
import asyncio
from typing import Union, Callable, Optional, List
import fractions
from enum import Enum

from aiortc.mediastreams import (
    AUDIO_PTIME,
    MediaStreamError,
    MediaStreamTrack,
    VideoStreamTrack,
)
from aiortc.contrib.media import REAL_TIME_FORMATS
import av
from av import AudioFrame, VideoFrame
from av.frame import Frame
from av.packet import Packet

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
logger = logging.getLogger()


async def async_do_nothing() -> None:
    pass


def do_nothing():
    pass


class MediaKind(Enum):
    VIDEO = "video"
    AUDIO = "audio"


class PlayerStreamTrack(MediaStreamTrack):
    __queue: "asyncio.Queue[Frame]"

    class Event:
        START = "start"
        STOP = "stop"

    def __init__(
        self,
        kind: MediaKind,
        on_start: Callable = lambda: None,
        on_stop: Callable = lambda: None,
    ):
        super().__init__()
        self.kind = kind.value
        self.__queue: "asyncio.Queue[Frame]" = asyncio.Queue()

        # In case user passes None to these parameters
        if not callable(on_start):
            on_start = do_nothing
        if not callable(on_stop):
            on_stop = do_nothing

        self.once(self.Event.START, on_start)
        self.once(self.Event.STOP, on_stop)

    async def recv(self) -> Union[Frame, Packet]:
        """
        This method will be called by aiortc PeerConnection media stream
        to get media, in the form of PyAV frame
        """

        if self.readyState != "live":
            raise MediaStreamError

        self.emit(self.Event.START)

        data = await self.__queue.get()

        if data is None:
            self.stop()
            raise MediaStreamError

        return data

    async def put_frame(self, frame: Frame) -> None:
        await self.__queue.put(frame)

    async def clear_queue(self) -> None:
        try:
            while not self.__queue.empty():
                self.__queue.get_nowait()
                self.__queue.task_done()
        except asyncio.QueueEmpty:
            return


def stream_media(
    event_loop: asyncio.AbstractEventLoop,
    container,
    streams,
    audio_stream_track: PlayerStreamTrack,
    video_stream_track: PlayerStreamTrack,
    thread_start_event: threading.Event,
    thread_quit_event: threading.Event,
    # proxy_method,
    throttle_playback: bool,
    loop_playback: bool,
) -> None:
    audio_sample_rate = 48000
    audio_samples = 0
    audio_time_base = fractions.Fraction(1, audio_sample_rate)
    audio_resampler = av.AudioResampler(
        format="s16",
        layout="stereo",
        rate=audio_sample_rate,
        frame_size=int(audio_sample_rate * AUDIO_PTIME),
    )

    video_first_pts = None

    thread_start_event.wait()

    send_audio_frame_coroutine: asyncio.Future = None
    send_video_frame_coroutine: asyncio.Future = None
    frame_time = None
    start_time = time.time()

    while not thread_quit_event.is_set():
        # read up to 1 second ahead
        if throttle_playback:
            elapsed_time = time.time() - start_time
            if frame_time and frame_time > elapsed_time + 1:
                time.sleep(0.1)

        try:
            # This is just my guess:
            # aiortc only takes 1 audio stream and 1 video stream, so only
            # decode the streams that we are really going to stream
            frame = next(container.decode(*streams))
        except Exception as exc:
            if isinstance(exc, av.FFmpegError) and exc.errno == errno.EAGAIN:
                logger.error(exc)
                time.sleep(0.01)
                continue

            if isinstance(exc, StopIteration) and loop_playback:
                container.seek(0)
                continue

            # Insert None as frame to stop the stream track, if it's still receiving
            if audio_stream_track:
                asyncio.run_coroutine_threadsafe(
                    audio_stream_track.put_frame(None), event_loop
                ).result()
            if video_stream_track:
                asyncio.run_coroutine_threadsafe(
                    video_stream_track.put_frame(None), event_loop
                ).result()

            break

        # print(frame)

        if isinstance(frame, AudioFrame) and audio_stream_track:
            for frame in audio_resampler.resample(frame):
                # fix timestamps
                frame.pts = audio_samples
                frame.time_base = audio_time_base
                audio_samples += frame.samples

                frame_time = frame.time

                # Don't get the results (meaning don't await)
                # to minimize the delay
                send_audio_frame_coroutine = asyncio.run_coroutine_threadsafe(
                    audio_stream_track.put_frame(frame), event_loop
                )
                # asyncio.run_coroutine_threadsafe(
                #     proxy_method(frame),
                #     loop=event_loop,
                # )
        elif isinstance(frame, VideoFrame) and video_stream_track:
            if frame.pts is None:
                logger.warning(
                    f"MediaPlayer({container.name}) Skipping video frame with no pts",
                )
                continue

            # video from a webcam doesn't start at pts 0, cancel out offset
            if video_first_pts is None:
                video_first_pts = frame.pts
            frame.pts -= video_first_pts

            frame_time = frame.time

            # Don't get the results (meaning don't await)
            # to minimize the delay
            send_video_frame_coroutine = asyncio.run_coroutine_threadsafe(
                video_stream_track.put_frame(frame),
                loop=event_loop,
            )
            # asyncio.run_coroutine_threadsafe(
            #     proxy_method(frame),
            #     loop=event_loop,
            # )

    # Get the results here to make sure the coroutine is awaited
    if send_audio_frame_coroutine:
        send_audio_frame_coroutine.result()
    if send_video_frame_coroutine:
        send_video_frame_coroutine.result()

    container.close()


class MediaPlayer:
    """
    A media source that reads audio and/or video from a file.

    Examples:

    .. code-block:: python

        # Open a video file.
        player = MediaPlayer('/path/to/some.mp4')

        # Open an HTTP stream.
        player = MediaPlayer(
            'http://download.tsi.telecom-paristech.fr/'
            'gpac/dataset/dash/uhd/mux_sources/hevcds_720p30_2M.mp4')

        # Open webcam on Linux.
        player = MediaPlayer('/dev/video0', format='v4l2', options={
            'video_size': '640x480'
        })

        # Open webcam on OS X.
        player = MediaPlayer('default:none', format='avfoundation', options={
            'video_size': '640x480'
        })

        # Open webcam on Windows.
        player = MediaPlayer('video=Integrated Camera', format='dshow', options={
            'video_size': '640x480'
        })

    :param file: The path to a file, or a file-like object.
    :param format: The format to use, defaults to autodect.
    :param options: Additional options to pass to FFmpeg.
    :param timeout: Open/read timeout to pass to FFmpeg.
    :param loop: Whether to repeat playback indefinitely (requires a seekable file).
    """

    __event_loop: asyncio.AbstractEventLoop
    __loop_playback: bool
    __throttle_playback: bool

    __container: av.container.OutputContainer
    __streams: List
    """Contains the container streams used by this player"""
    __audio_stream_track: Optional[PlayerStreamTrack]
    __video_stream_track: Optional[PlayerStreamTrack]

    __stream_media_thread_start: threading.Event
    __stream_media_thread_quit: threading.Event
    __stream_media_thread: threading.Thread

    def __init__(
        self,
        file,
        format=None,
        options={},
        timeout=None,
        event_loop: asyncio.AbstractEventLoop = None,
        loop_playback=False,
        # proxy_method=async_do_nothing,
    ):
        self.__stream_media_thread_start: threading.Event = threading.Event()
        self.__stream_media_thread_quit: threading.Event = threading.Event()

        # self.__proxy_method = proxy_method
        if event_loop:
            self.__event_loop = event_loop
        else:
            self.__event_loop = asyncio.get_event_loop()

        self.__container = av.open(
            file=file, format=format, mode="r", options=options, timeout=timeout
        )

        # check whether we need to throttle playback
        container_format = set(self.__container.format.name.split(","))
        self.__throttle_playback = not container_format.intersection(REAL_TIME_FORMATS)

        # check whether the looping is supported
        assert (
            not loop_playback or self.__container.duration is not None
        ), "The `loop` argument requires a seekable file"
        self.__loop_playback = loop_playback

        # examine streams
        self.__streams = []
        self.__audio_stream_track = None
        self.__video_stream_track = None
        for stream in self.__container.streams:
            if stream.type == MediaKind.AUDIO.value and not self.__audio_stream_track:
                self.__audio_stream_track = PlayerStreamTrack(
                    kind=MediaKind.AUDIO, on_start=self.__stream_media_thread_start.set
                )
                self.__streams.append(stream)
            elif stream.type == MediaKind.VIDEO.value and not self.__video_stream_track:
                self.__video_stream_track = PlayerStreamTrack(
                    kind=MediaKind.VIDEO, on_start=self.__stream_media_thread_start.set
                )
                self.__streams.append(stream)

        # Create and start the thread
        self.__stream_media_thread: threading.Thread = threading.Thread(
            name="stream-media",
            target=stream_media,
            args=(
                self.__event_loop,
                self.__container,
                self.__streams,
                self.__audio_stream_track,
                self.__video_stream_track,
                self.__stream_media_thread_start,
                self.__stream_media_thread_quit,
                self.__throttle_playback,
                self.__loop_playback,
                # self.__proxy_method,
            ),
        )
        # Start the thread first to reduce time to first frame
        self.__stream_media_thread.start()

    @property
    def stream_tracks(self) -> List[MediaStreamTrack]:
        """
        A list of :class:`aiortc.MediaStreamTrack` instances.
        """
        stream_tracks = []

        if self.__audio_stream_track:
            stream_tracks.append(self.__audio_stream_track)

        if self.__video_stream_track:
            stream_tracks.append(self.__video_stream_track)
        else:
            # Add dummy video track because aiortc cannot open
            # PC without at least 1 media stream
            stream_tracks.append(VideoStreamTrack())

        return stream_tracks

    def stop(self) -> None:
        self.__stream_media_thread_quit.set()
        # Cannot join here because it will block the event loop and the
        # thread won't exit because it's trying to put a frame into async queue
        # self.__stream_media_thread.join()
