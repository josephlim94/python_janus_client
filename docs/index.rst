.. Janus Client documentation master file, created by
   sphinx-quickstart on Sat Mar 13 18:02:45 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Janus Client
==================================================

`Janus`_ WebRTC gateway Python asyncio client.

.. _JANUS: https://github.com/meetecho/janus-gateway

.. toctree::
   :maxdepth: 2
   :caption: Contents:


Key Features
============

- Supports HTTP/s and WebSockets communication with Janus.
- Supports Janus plugin:
   - EchoTest Plugin
   - VideoCall Plugin
   - VideoRoom Plugin
- Extendable Transport class and Plugin class

.. _aiohttp-installation:

Library Installation
====================

.. code-block:: bash

   $ pip install janus-client

Getting Started
===============

Client example
--------------

.. code-block:: python

  import aiohttp
  import asyncio

  async def main():

      async with aiohttp.ClientSession() as session:
          async with session.get('http://python.org') as response:

              print("Status:", response.status)
              print("Content-type:", response.headers['content-type'])

              html = await response.text()
              print("Body:", html[:15], "...")

  asyncio.run(main())

This prints:

.. code-block:: text

    Status: 200
    Content-type: text/html; charset=utf-8
    Body: <!doctype html> ...

Coming from :term:`requests` ? Read :ref:`why we need so many lines <aiohttp-request-lifecycle>`.

Table Of Contents
==================

.. toctree::
   :name: mastertoc
   :maxdepth: 2

   session
   plugin
   transport