import asyncio
import logging
import threading
from typing import Optional, Set, Union
import subprocess
import time

from av import VideoFrame
from av.frame import Frame
from av.packet import Packet
import numpy as np
import fractions

from aiortc.mediastreams import MediaStreamError, MediaStreamTrack

logger = logging.getLogger(__name__)

REAL_TIME_FORMATS = [
    "alsa",
    "android_camera",
    "avfoundation",
    "bktr",
    "decklink",
    "dshow",
    "fbdev",
    "gdigrab",
    "iec61883",
    "jack",
    "kmsgrab",
    "openal",
    "oss",
    "pulse",
    "sndio",
    "rtsp",
    "v4l2",
    "vfwcap",
    "x11grab",
]


async def blackhole_consume(track):
    while True:
        try:
            await track.recv()
        except MediaStreamError:
            return


class MediaBlackhole:
    """
    A media sink that consumes and discards all media.
    """

    def __init__(self):
        self.__tracks = {}

    def addTrack(self, track):
        """
        Add a track whose media should be discarded.

        :param track: A :class:`aiortc.MediaStreamTrack`.
        """
        if track not in self.__tracks:
            self.__tracks[track] = None

    async def start(self):
        """
        Start discarding media.
        """
        for track, task in self.__tracks.items():
            if task is None:
                self.__tracks[track] = asyncio.ensure_future(blackhole_consume(track))

    async def stop(self):
        """
        Stop discarding media.
        """
        for task in self.__tracks.values():
            if task is not None:
                task.cancel()
        self.__tracks = {}


class PlayerStreamTrack(MediaStreamTrack):
    def __init__(self, player, kind):
        super().__init__()
        self.kind = kind
        self._player = player
        self._queue = asyncio.Queue()
        self._start = None

    async def recv(self) -> Union[Frame, Packet]:
        if self.readyState != "live":
            raise MediaStreamError

        self._player._start(self)
        data = await self._queue.get()
        if data is None:
            self.stop()
            raise MediaStreamError
        # data_time = None

        # # control playback rate
        # if (
        #     self._player is not None
        #     and self._player._throttle_playback
        #     and data_time is not None
        # ):
        #     if self._start is None:
        #         self._start = time.time() - data_time
        #     else:
        #         wait = self._start + data_time - time.time()
        #         await asyncio.sleep(wait)

        return data

    def stop(self):
        super().stop()
        if self._player is not None:
            self._player._stop(self)
            self._player = None


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

        # Open webcam on Windows.
        player = MediaPlayer('video=Integrated Camera', format='dshow', options={
            'video_size': '640x480'
        })

    :param file: The path to a file, or a file-like object.
    :param format: The format to use, defaults to autodect.
    :param options: Additional options to pass to FFmpeg.
    :param timeout: Open/read timeout to pass to FFmpeg.
    :param loop: Whether to repeat playback indefinitely (requires a seekable file).
    """

    def __init__(
        self,
        ffmpeg_input,
        width: int,
        height: int,
    ):
        self.__thread: Optional[threading.Thread] = None
        self.__thread_quit: Optional[threading.Event] = None

        self.__ffmpeg_input = ffmpeg_input
        self.__width = width
        self.__height = height

        # examine streams
        self.__started: Set[MediaStreamTrack] = set()
        self.__audio: Optional[PlayerStreamTrack] = None
        self.__video = PlayerStreamTrack(self, kind="video")

        self._throttle_playback = False
        self._loop_playback = False

    @property
    def audio(self) -> MediaStreamTrack:
        """
        A :class:`aiortc.MediaStreamTrack` instance if the file contains audio.
        """
        return self.__audio

    @property
    def video(self) -> MediaStreamTrack:
        """
        A :class:`aiortc.MediaStreamTrack` instance if the file contains video.
        """
        return self.__video

    def player_worker_decode(
        self,
        loop,
        video_track,
        quit_event,
    ):
        logging.info("Thread 1: starting")
        pts = 0
        video_process: subprocess.Popen = self.__ffmpeg_input.output(
            "pipe:", format="rawvideo", pix_fmt="rgb24"
        ).run_async(pipe_stdout=True, pipe_stdin=True)

        count = 0
        total_time = 0
        total_cpu_time = 0
        while not quit_event.is_set():
            in_bytes = video_process.stdout.read(self.__width * self.__height * 3)
            if not in_bytes:
                break

            start_time = time.time()
            start_cpu_time = time.process_time()

            in_frame = np.frombuffer(in_bytes, np.uint8).reshape(
                [self.__height, self.__width, 3]
            )
            frame = VideoFrame.from_ndarray(in_frame, format="rgb24")

            frame.pts = pts
            pts += 1
            frame.time_base = fractions.Fraction(1, 48000)

            total_time += time.time() - start_time
            total_cpu_time += time.process_time() - start_cpu_time
            count += 1

            # logging.info(frame)
            asyncio.run_coroutine_threadsafe(video_track._queue.put(frame), loop)

        video_process.communicate(b"q", timeout=1)
        video_process.wait()

        logging.info("Thread 1: finishing")
        logger.info(
            f"time: {total_time * 1000 / count}ms | cpu time: {total_cpu_time * 1000 / count}ms"
        )

    def _start(self, track: PlayerStreamTrack) -> None:
        self.__started.add(track)
        if self.__thread is None:
            self.__log_debug("Starting worker thread")
            self.__thread_quit = threading.Event()
            self.__thread = threading.Thread(
                name="media-player",
                target=self.player_worker_decode,
                args=(
                    asyncio.get_event_loop(),
                    self.__video,
                    self.__thread_quit,
                ),
            )
            self.__thread.start()

    def _stop(self, track: PlayerStreamTrack) -> None:
        self.__started.discard(track)

        if not self.__started and self.__thread is not None:
            self.__log_debug("Stopping worker thread")
            self.__thread_quit.set()
            self.__thread.join()
            self.__thread = None

        # if not self.__started and self.__container is not None:
        #     self.__container.close()
        #     self.__container = None

    def __log_debug(self, msg: str, *args) -> None:
        logger.debug(f"MediaPlayer(%s) {msg}", "asd", *args)
