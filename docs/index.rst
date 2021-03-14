.. Janus Client in Python documentation master file, created by
   sphinx-quickstart on Sat Mar 13 18:02:45 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Janus Client in Python's documentation!
==================================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Client
===============

.. autoclass:: janus_client.JanusClient
   :members: connect, disconnect, create_session
   :special-members: __init__

Session
=======

.. autoclass:: janus_client.JanusSession
   :members: create_plugin_handle, destroy

Plugin Handle
=============

Base Class
----------

.. autoclass:: janus_client.JanusPlugin
   :members:

VideoRoom Plugin
----------------

.. autoclass:: janus_client.plugin_video_room.JanusVideoRoomPlugin
   :members: