.. Janus Client documentation master file, created by
   sphinx-quickstart on Sat Mar 13 18:02:45 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Janus Client's documentation!
==================================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Transport
===============

.. autoclass:: janus_client.JanusTransport
   :members: _connect, _disconnect, _send, info, ping
   :special-members: __init__

Session
=======

.. autoclass:: janus_client.JanusSession
   :members: create, destroy, send, attach_plugin, detach_plugin

Plugin Handle
=============

Base Class
----------

.. autoclass:: janus_client.JanusPlugin
   :members: attach, destroy, send, handle_async_response, trickle

VideoRoom Plugin
----------------

.. autoclass:: janus_client.JanusVideoRoomPlugin
   :members: