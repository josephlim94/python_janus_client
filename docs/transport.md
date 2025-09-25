# Transport

Transport classes handle the actual communication with the Janus server. The transport method is automatically detected using regex patterns on the base_url parameter passed to the Session object.

## Base Transport Class

::: janus_client.transport.JanusTransport
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      docstring_section_style: table
      separate_signature: true
      show_signature_annotations: true

## HTTP Transport

The HTTP transport implementation provides communication with Janus server over HTTP/HTTPS using long polling for receiving messages.

::: janus_client.transport_http.JanusTransportHTTP
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      docstring_section_style: table
      separate_signature: true
      show_signature_annotations: true

### HTTP Transport Features

- **Protocol Support**: HTTP and HTTPS
- **Long Polling**: Efficient message receiving using long polling
- **Connection Pooling**: Reuses HTTP connections for efficiency
- **Session Management**: Automatic session lifecycle management
- **Error Recovery**: Automatic retry with exponential backoff

### HTTP Transport Usage

```python
import asyncio
from janus_client import JanusSession

async def main():
    # HTTP transport will be automatically selected for http/https URLs
    session = JanusSession(base_url="https://example.com/janus")
    
    async with session:
        # Transport handles all HTTP communication automatically
        info = await session.transport.info()
        print(f"Server info: {info}")
        
        # Send a ping to test connectivity
        ping_response = await session.transport.ping()
        print(f"Ping response: {ping_response}")

if __name__ == "__main__":
    asyncio.run(main())
```

## WebSocket Transport

The WebSocket transport implementation provides real-time, full-duplex communication with the Janus server.

::: janus_client.transport_websocket.JanusTransportWebsocket
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      docstring_section_style: table
      separate_signature: true
      show_signature_annotations: true

### WebSocket Transport Features

- **Full-Duplex Communication**: Real-time bidirectional messaging
- **Low Latency**: Direct WebSocket connection for minimal delay
- **Automatic Reconnection**: Handles connection drops gracefully
- **Message Queuing**: Buffers messages during reconnection
- **Keepalive Support**: Built-in ping/pong for connection health

### WebSocket Transport Usage

```python
import asyncio
from janus_client import JanusSession

async def main():
    # WebSocket transport will be automatically selected for ws/wss URLs
    session = JanusSession(base_url="wss://example.com/janus")
    
    async with session:
        # Transport handles all WebSocket communication automatically
        ping_response = await session.transport.ping()
        print(f"Ping response: {ping_response}")
        
        # Get server information
        info = await session.transport.info()
        print(f"Server info: {info}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Transport Selection

The transport is automatically selected based on the URL scheme provided to the session:

| URL Scheme | Transport Class | Description |
|------------|----------------|-------------|
| `http://` | `JanusTransportHTTP` | HTTP transport with long polling |
| `https://` | `JanusTransportHTTP` | HTTPS transport with long polling |
| `ws://` | `JanusTransportWebsocket` | WebSocket transport |
| `wss://` | `JanusTransportWebsocket` | Secure WebSocket transport |

### Transport Registration

Transport classes are registered using protocol matcher functions:

```python
# HTTP transport registration
def protocol_matcher(base_url: str) -> bool:
    return base_url.startswith(("http://", "https://"))

JanusTransport.register_transport(protocol_matcher, JanusTransportHTTP)
```

## Custom Transport Implementation

You can create custom transport implementations by inheriting from `JanusTransport` and implementing the required abstract methods:

```python
from janus_client import JanusTransport
from typing import Dict, Any

class MyCustomTransport(JanusTransport):
    def __init__(self, base_url: str, **kwargs):
        super().__init__(base_url, **kwargs)
        # Initialize custom transport-specific attributes
        self._connection = None
    
    async def _connect(self) -> None:
        """Establish connection to the Janus server."""
        # Implement your connection logic here
        print(f"Connecting to {self.base_url}")
        # self._connection = await create_custom_connection(self.base_url)
    
    async def _disconnect(self) -> None:
        """Close the connection to the Janus server."""
        # Implement your disconnection logic here
        if self._connection:
            # await self._connection.close()
            self._connection = None
    
    async def _send(self, message: Dict[str, Any]) -> None:
        """Send a message to the Janus server."""
        # Implement your message sending logic here
        if not self._connection:
            raise ConnectionError("Not connected")
        # await self._connection.send(message)

# Protocol matcher function
def protocol_matcher(base_url: str) -> bool:
    """Check if this transport can handle the URL."""
    return base_url.startswith("mycustom://")

# Register the custom transport
JanusTransport.register_transport(protocol_matcher, MyCustomTransport)
```

## Transport Configuration

Transport classes accept various configuration options through the session constructor:

```python
session = JanusSession(
    base_url="wss://example.com/janus",
    # Common transport options
    timeout=30.0,           # Request timeout in seconds
    max_retries=3,          # Maximum retry attempts
    retry_delay=1.0,        # Initial retry delay in seconds
    keepalive_interval=30,  # Keepalive ping interval in seconds
    
    # HTTP-specific options
    max_connections=10,     # Maximum HTTP connections in pool
    
    # WebSocket-specific options
    ping_interval=20,       # WebSocket ping interval
    ping_timeout=10,        # WebSocket ping timeout
)
```

## Error Handling and Recovery

All transport implementations provide robust error handling:

### Connection Failures

```python
import asyncio
from janus_client import JanusSession

async def robust_connection():
    session = JanusSession(
        base_url="wss://example.com/janus",
        max_retries=5,
        retry_delay=2.0
    )
    
    try:
        async with session:
            # Transport will automatically retry on connection failures
            await session.transport.ping()
    except ConnectionError as e:
        print(f"Failed to connect after retries: {e}")
    except TimeoutError as e:
        print(f"Connection timed out: {e}")
```

### Network Timeouts

```python
async def timeout_handling():
    session = JanusSession(
        base_url="https://example.com/janus",
        timeout=10.0  # 10 second timeout
    )
    
    try:
        async with session:
            # This will timeout if server doesn't respond within 10 seconds
            info = await session.transport.info()
    except asyncio.TimeoutError:
        print("Request timed out")
```

### Automatic Reconnection

WebSocket transport supports automatic reconnection:

```python
async def websocket_with_reconnection():
    session = JanusSession(
        base_url="wss://example.com/janus",
        max_retries=10,        # Retry up to 10 times
        retry_delay=1.0,       # Start with 1 second delay
        keepalive_interval=30  # Send keepalive every 30 seconds
    )
    
    async with session:
        # Connection will be automatically maintained
        # and reconnected if it drops
        plugin = JanusEchoTestPlugin()
        await plugin.attach(session)
        
        # Long-running operation
        await asyncio.sleep(300)  # 5 minutes
        
        await plugin.destroy()
```

## Performance Considerations

### HTTP vs WebSocket

**Use HTTP transport when:**
- Simple request/response patterns
- Firewall restrictions on WebSocket
- Stateless operations
- Lower connection overhead is acceptable

**Use WebSocket transport when:**
- Real-time communication is required
- Low latency is important
- Frequent bidirectional messaging
- Long-lived connections

### Connection Pooling

HTTP transport uses connection pooling for efficiency:

```python
# Multiple sessions can share the same connection pool
session1 = JanusSession(base_url="https://example.com/janus")
session2 = JanusSession(base_url="https://example.com/janus")

# Both sessions will reuse HTTP connections
```

### Resource Management

Always properly close sessions to release transport resources:

```python
# Good: Using context manager
async with session:
    # Transport resources are automatically cleaned up
    pass

# Also good: Manual cleanup
session = JanusSession(base_url="wss://example.com/janus")
try:
    await session.create()
    # Use session
finally:
    await session.destroy()  # Ensures transport cleanup
```

## Debugging Transport Issues

### Enable Logging

```python
import logging

# Enable debug logging for transport layer
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('janus_client.transport')
logger.setLevel(logging.DEBUG)
```

### Monitor Connection State

```python
async def monitor_connection():
    session = JanusSession(base_url="wss://example.com/janus")
    
    async with session:
        # Check if transport is connected
        try:
            await session.transport.ping()
            print("Transport is connected and responsive")
        except Exception as e:
            print(f"Transport issue: {e}")
```

### Network Analysis

For debugging network issues:

1. **Check server accessibility**: Verify the Janus server is running and accessible
2. **Firewall rules**: Ensure WebSocket connections are allowed
3. **SSL certificates**: Verify HTTPS/WSS certificates are valid
4. **Network latency**: Test network conditions between client and server
5. **Server logs**: Check Janus server logs for connection issues

## Transport Protocol Details

### HTTP Transport Protocol

The HTTP transport uses the following endpoints:

- `GET /janus/info` - Server information
- `POST /janus` - Create session
- `POST /janus/{session_id}` - Session operations
- `GET /janus/{session_id}` - Long polling for messages
- `POST /janus/{session_id}/{handle_id}` - Plugin operations

### WebSocket Transport Protocol

The WebSocket transport uses a single WebSocket connection for all communication:

- Connection: `wss://example.com/janus`
- Protocol: `janus-protocol`
- Messages: JSON-formatted Janus protocol messages
- Keepalive: Automatic ping/pong frames
