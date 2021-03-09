
import sys
import logging
from datetime import timedelta

import gi
gi.require_version("GLib", "2.0")
gi.require_version("GObject", "2.0")
gi.require_version("Gst", "1.0")
from gi.repository import Gst


logging.basicConfig(level=logging.DEBUG,
                    format="[%(name)s] [%(levelname)8s] - %(message)s")
logger = logging.getLogger(__name__)


class Player(object):
    def __init__(self):
        # Initialize GStreamer
        Gst.init(None)

        # Create elements as class members so that it can be accessed by member fns. easily
        self.playbin = Gst.ElementFactory.make(
            "playbin", "playbin")  # Our one and only element
        self.playing = False  # Are we in the PLAYING state
        self.terminate = False  # Should we terminate execution?
        self.seek_enabled = False  # Is seeking enabled for this media?
        self.seek_done = False  # Have we performed the seek already?
        # How long does this media last, in nanoseconds
        self.duration = Gst.CLOCK_TIME_NONE

        if not self.playbin:
            logger.error("Not all elements could be created.")
            sys.exit(1)

        # Set the URI to play
        self.playbin.set_property(
            "uri", "https://www.freedesktop.org/software/gstreamer-sdk/data/media/sintel_trailer-480p.webm"
        )

    def play(self):
        """Start playing the pipeline"""
        # Dont start again if we are already playing
        if self.playing:
            return

        # Start playing
        ret = self.playbin.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            logger.error("Unable to set the pipeline to the playing state.")
            sys.exit(1)

        # Listen to the bus
        bus = self.playbin.get_bus()
        while not self.terminate:
            msg = bus.timed_pop_filtered(
                100 * Gst.MSECOND,
                (
                    Gst.MessageType.STATE_CHANGED
                    | Gst.MessageType.ERROR
                    | Gst.MessageType.EOS
                    | Gst.MessageType.DURATION_CHANGED
                ),
            )

            # Parse message
            if msg:
                self.handle_message(msg)
                continue

            # We got no message. this means the timeout expired
            if self.playing:
                current = -1
                # Query the current position of the stream
                ret, current = self.playbin.query_position(Gst.Format.TIME)
                if not ret:
                    logger.error("Could not query current position.")

                # If we didn't know it yet, query the stream duration
                if self.duration == Gst.CLOCK_TIME_NONE:
                    ret, self.duration = self.playbin.query_duration(
                        Gst.Format.TIME)
                    if not ret:
                        logger.error("Could not query current duration.")

                # Print current position and total duration
                logger.debug(
                    "Position {} / {}".format(
                        timedelta(seconds=current / 10 **
                                  9), timedelta(seconds=self.duration / 10 ** 9)
                    )
                )

                # If seeking is enabled, we have not done it yet, and the time is right, seek
                if self.seek_enabled and not self.seek_done and current > 10 * Gst.SECOND:
                    logger.info("Reached 10s, performing seek...")
                    self.playbin.seek_simple(
                        Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, 30 * Gst.SECOND
                    )
                    self.seek_done = True
        self.playbin.set_state(Gst.State.NULL)

    def handle_message(self, msg):
        t = msg.type
        if t == Gst.MessageType.ERROR:
            err, debug_info = msg.parse_error()
            logger.error(
                f"Error received from element {msg.src.get_name()}: {err}")
            logger.error(
                f"Debugging information: {debug_info if debug_info else 'none'}")
            self.terminate = True
        elif t == Gst.MessageType.EOS:
            logger.info("End-Of-Stream reached.")
            self.terminate = True
        elif t == Gst.MessageType.DURATION_CHANGED:
            # The duration has changed, mark the current one as invalid
            self.duration = Gst.CLOCK_TIME_NONE
        elif t == Gst.MessageType.STATE_CHANGED:
            old_state, new_state, pending_state = msg.parse_state_changed()
            if msg.src == self.playbin:
                logger.info(
                    "Pipeline state changed from '{}' to '{}'".format(
                        Gst.Element.state_get_name(
                            old_state), Gst.Element.state_get_name(new_state)
                    )
                )

                # Remember whether we are in the PLAYING state or not
                self.playing = new_state == Gst.State.PLAYING

                if self.playing:
                    # We just moved to PLAYING. Check if seeking is possible
                    query = Gst.Query.new_seeking(Gst.Format.TIME)
                    if self.playbin.query(query):
                        fmt, self.seek_enabled, start, end = query.parse_seeking()

                        if self.seek_enabled:
                            logger.info(
                                "Seeking is ENABLED (from {} to {})".format(
                                    timedelta(seconds=start / 10 **
                                              9), timedelta(seconds=end / 10 ** 9)
                                )
                            )
                        else:
                            logger.info("Seeking is DISABLED for this stream.")
                    else:
                        logger.error("Seeking query failed.")

        else:
            # We should not reach here
            logger.error("Unexpected message received.")


if __name__ == "__main__":
    p = Player()
    p.play()
