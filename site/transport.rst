

Transport
===============

Transport method is detected using regex on base_url parameter passed to Session object.


Base Class
---------------

.. autoclass:: janus_client.JanusTransport
   :members: _connect, _disconnect, _send, info, ping, dispatch_session_created, dispatch_session_destroyed, register_transport, create_transport
   :special-members: __init__

HTTP
---------------

.. autoclass:: janus_client.JanusTransportHTTP
   :members:

Websockets
---------------

.. autoclass:: janus_client.JanusTransportWebsocket
   :members: