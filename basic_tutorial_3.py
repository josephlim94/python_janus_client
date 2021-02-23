import logging
import signal
import sys

import gi

gi.require_version("GLib", "2.0")
gi.require_version("GObject", "2.0")
gi.require_version("Gst", "1.0")

from gi.repository import Gst


logging.basicConfig(level=logging.DEBUG, format="[%(name)s] [%(levelname)8s] - %(message)s")
logger = logging.getLogger(__name__)


class Player(object):
    def __init__(self):
        # Initialize GStreamer
        Gst.init(sys.argv[1:])

        try:
            # Create the Gst elements as class members so that it can be accessed by member fns. easily
            self.pipeline = Gst.Pipeline.new("test-pipeline")
            self.source = Gst.ElementFactory.make("uridecodebin", "source")
            self.convert = Gst.ElementFactory.make("audioconvert", "convert")
            self.resample = Gst.ElementFactory.make("audioresample", "resample")
            self.sink = Gst.ElementFactory.make("autoaudiosink", "sink")
        except Gst.AddError as e:
            logger.error("Not all elements could be created.")
            sys.exit(1)

        # Build the pipeline. Note that we are NOT linking the source at this
        # point. We will do it later.
        self.pipeline.add(self.source, self.convert, self.resample, self.sink)
        if not all((self.convert.link(self.resample), self.resample.link(self.sink))):
            logger.error("Elements could not be linked")
            sys.exit(1)

        # Set the URI to play
        self.source.props.uri = (
            "https://www.freedesktop.org/software/gstreamer-sdk/data/media/sintel_trailer-480p.webm"
        )

        # Connect to the pad-added signal
        self.source.connect("pad-added", self.pad_added_handler)

    def play(self):

        # Start playing
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            logger.error("Unable to set the pipeline to the playing state.")
            sys.exit(1)

        # Handle KeyboardInterrupts (Ctrl+C) and SIGINTs gracefully by sending EOS
        signal.signal(
            signal.SIGINT,
            lambda *_: self.pipeline.send_event(Gst.Event.new_eos()) and logger.error("SIGINT detected, Exiting"),
        )

        # listen to the bus
        bus = self.pipeline.get_bus()

        while True:
            msg = bus.timed_pop_filtered(
                0.5 * Gst.SECOND, Gst.MessageType.STATE_CHANGED | Gst.MessageType.ERROR | Gst.MessageType.EOS
            )

            if not msg:
                continue

            # Parse message
            t = msg.type
            if t == Gst.MessageType.ERROR:
                err, debug_info = msg.parse_error()
                logger.error(f"Error received from element {msg.src.get_name()}: {err.message}")
                logger.error(f"Debugging information: {debug_info if debug_info else 'none'}")
                break
            elif t == Gst.MessageType.EOS:
                logger.info("End-Of-Stream reached")
                break
            elif t == Gst.MessageType.STATE_CHANGED:
                # We are only interested in state-changed messages from the pipeline
                if msg.src == self.pipeline:
                    old_state, new_state, pending_state = msg.parse_state_changed()
                    logger.info(f"Pipeline state changed from {old_state.value_nick} to {new_state.value_nick}")
            else:
                # We should not reach here
                logger.error("Unexpected message received.")

        self.pipeline.set_state(Gst.State.NULL)

    def pad_added_handler(self, src, new_pad):
        """This function will be called by the pad-added signal"""
        sink_pad = self.convert.get_static_pad("sink")
        logger.info(f"Received new pad '{new_pad.get_name()}' from '{src.get_name()}'")

        # If our converter is already linked, we have nothing to do here
        if sink_pad.is_linked():
            logger.info("We are already linked. Ignoring.")
            return

        # Check the new pad's type
        new_pad_caps = new_pad.get_current_caps()
        new_pad_struct = new_pad_caps.get_structure(0)
        new_pad_type = new_pad_struct.get_name()

        if not new_pad_type.startswith("audio/x-raw"):
            logger.info(f"It has type '{new_pad_type}' which is not raw audio. Ignoring.")
            return

        # Attempt the link
        ret = new_pad.link(sink_pad)
        if not ret == Gst.PadLinkReturn.OK:
            logger.info(f"Type is '{new_pad_type}' but link failed")
        else:
            logger.info(f"Link succeeded (type '{new_pad_type}')")

        return


if __name__ == "__main__":
    p = Player()
    p.play()