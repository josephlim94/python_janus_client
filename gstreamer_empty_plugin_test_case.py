
import logging
import timeit
import traceback
import time

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, GLib

# GObject.threads_init()
Gst.init(None)


class GstPluginPy(Gst.Element):

    __gstmeta__ = ("gstplugin_py",
                   "Gst Plugin Python Implementation",
                   "gst.Element wraps processing model written in Python",
                   "DataAI")

    __gstmetadata__ = __gstmeta__

    _srctemplate = Gst.PadTemplate.new('src', Gst.PadDirection.SRC,
                                       Gst.PadPresence.ALWAYS,
                                       Gst.Caps.from_string("video/x-raw,format=RGB"))

    _sinktemplate = Gst.PadTemplate.new('sink', Gst.PadDirection.SINK,
                                        Gst.PadPresence.ALWAYS,
                                        Gst.Caps.from_string("video/x-raw,format=RGB"))

    __gsttemplates__ = (_srctemplate, _sinktemplate)

    __gproperties__ = {
        "model": (GObject.TYPE_PYOBJECT,
                  "model",
                  "Contains model that implements IDataTransform",
                  GObject.ParamFlags.READWRITE)
    }

    def __init__(self):
        Gst.Element.__init__(self)

        self.sinkpad = Gst.Pad.new_from_template(self._sinktemplate, 'sink')
        self.sinkpad.set_chain_function_full(self.chainfunc, None)
        self.sinkpad.set_event_function_full(self.eventfunc, None)
        self.add_pad(self.sinkpad)

        self.srcpad = Gst.Pad.new_from_template(self._srctemplate, 'src')
        self.srcpad.set_event_function_full(self.srceventfunc, None)
        self.srcpad.set_query_function_full(self.srcqueryfunc, None)
        self.add_pad(self.srcpad)

        self.model = None

    def chainfunc(self, pad, parent, buffer):

        try:
            if self.model is not None:
                item = {
                    "pad": pad,
                    "buffer": buffer,
                    "timeout": 0.01
                }
                self.model.process(**item)
        except Exception as e:
            logging.error(e)
            traceback.print_exc()

        return self.srcpad.push(buffer)

    def do_get_property(self, prop):
        if prop.name == 'model':
            return self.model
        else:
            raise AttributeError('unknown property %s' % prop.name)

    def do_set_property(self, prop, value):
        if prop.name == 'model':
            self.model = value
        else:
            raise AttributeError('unknown property %s' % prop.name)

    def eventfunc(self, pad, parent, event):
        return self.srcpad.push_event(event)

    def srcqueryfunc(self, pad, object, query):
        return self.sinkpad.query(query)

    def srceventfunc(self, pad, parent, event):
        return self.sinkpad.push_event(event)


def register(class_info):

    def init(plugin, plugin_impl, plugin_name):
        type_to_register = GObject.type_register(plugin_impl)
        return Gst.Element.register(plugin, plugin_name, 0, type_to_register)

    # Parameters explanation
    # https://lazka.github.io/pgi-docs/Gst-1.0/classes/Plugin.html#Gst.Plugin.register_static
    version = '14.1'
    gstlicense = 'LGPL'
    origin = ''
    source = class_info.__gstmeta__[1]
    package = class_info.__gstmeta__[0]
    name = class_info.__gstmeta__[0]
    description = class_info.__gstmeta__[2]
    def init_function(plugin): return init(plugin, class_info, name)

    if not Gst.Plugin.register_static(Gst.VERSION_MAJOR, Gst.VERSION_MINOR,
                                      name, description,
                                      init_function, version, gstlicense,
                                      source, package, origin):
        raise ImportError("Plugin {} not registered".format(name))
    return True


register(GstPluginPy)
