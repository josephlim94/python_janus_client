# Transport

Transport method is detected using regex on base_url parameter passed to Session object.

## Base Class

### `JanusTransport`

Base class for all transport implementations. Transport classes handle the actual communication with the Janus server.

#### Constructor

```python
JanusTransport(base_url: str, **kwargs)
```

**Parameters:**
- `base_url` (str): The base URL of the Janus server
- `**kwargs`: Additional transport-specific configuration options

#### Methods

##### `_connect()`

```python
async def _connect() -> None
```

Establish connection to the Janus server. This is an abstract method that must be implemented by subclasses.

##### `_disconnect()`

```python
async def _disconnect() -> None
```

Close the connection to the Janus server. This is an abstract method that must be implemented by subclasses.

##### `_send(message)`

```python
async def _send(message: Dict[str, Any]) -> None
```

Send a message to the Janus server. This is an abstract method that must be implemented by subclasses.

**Parameters:**
- `message` (Dict[str, Any]): The message to send

##### `info()`

```python
async def info() -> Dict[str, Any]
```

Get server information from Janus.

**Returns:**
- `Dict[str, Any]`: Server information response

##### `ping()`

```python
async def ping() -> Dict[str, Any]
```

Send a ping to the Janus server to check connectivity.

**Returns:**
- `Dict[str, Any]`: Ping response

##### `dispatch_session_created(session)`

```python
def dispatch_session_created(session: JanusSession) -> None
```

Notify the transport that a session has been created.

**Parameters:**
- `session` (JanusSession): The created session

##### `dispatch_session_destroyed(session)`

```python
def dispatch_session_destroyed(session: JanusSession) -> None
```

Notify the transport that a session has been destroyed.

**Parameters:**
- `session` (JanusSession): The destroyed session

##### `register_transport(transport_class)`

```python
@staticmethod
def register_transport(transport_class: Type[JanusTransport]) -> None
```

Register a transport class for automatic detection.

**Parameters:**
- `transport_class` (Type[JanusTransport]): The transport class to register

##### `create_transport(base_url, **kwargs)`

```python
@staticmethod
def create_transport(base_url: str, **kwargs) -> JanusTransport
```

Create a transport instance based on the base URL.

**Parameters:**
- `base_url` (str): The base URL to determine transport type
- `**kwargs`: Additional configuration options

**Returns:**
- `JanusTransport`: The appropriate transport instance

## HTTP Transport

### `JanusTransportHTTP`

HTTP/HTTPS transport implementation for communicating with Janus server over HTTP.

#### Features

- Supports both HTTP and HTTPS protocols
- Uses long polling for receiving messages
- Automatic session management
- Connection pooling for efficiency

#### URL Format

```
http://example.com/janus
https://example.com/janus
```

#### Usage Example

```python
import asyncio
from janus_client import JanusSession

async def main():
    # HTTP transport will be automatically selected
    session = JanusSession(base_url="https://example.com/janus")
    
    async with session:
        # Transport handles all HTTP communication
        info = await session.transport.info()
        print(f"Server info: {info}")

if __name__ == "__main__":
    asyncio.run(main())
```

## WebSocket Transport

### `JanusTransportWebsocket`

WebSocket transport implementation for real-time communication with Janus server.

#### Features

- Full-duplex communication
- Real-time message delivery
- Automatic reconnection handling
- Lower latency than HTTP transport

#### URL Format

```
ws://example.com/janus
wss://example.com/janus
```

#### Usage Example

```python
import asyncio
from janus_client import JanusSession

async def main():
    # WebSocket transport will be automatically selected
    session = JanusSession(base_url="wss://example.com/janus")
    
    async with session:
        # Transport handles all WebSocket communication
        ping_response = await session.transport.ping()
        print(f"Ping response: {ping_response}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Transport Selection

The transport is automatically selected based on the URL scheme:

| URL Scheme | Transport Class |
|------------|----------------|
| `http://` | `JanusTransportHTTP` |
| `https://` | `JanusTransportHTTP` |
| `ws://` | `JanusTransportWebsocket` |
| `wss://` | `JanusTransportWebsocket` |

## Custom Transport Implementation

You can create custom transport implementations by inheriting from `JanusTransport`:

```python
from janus_client import JanusTransport
from typing import Dict, Any

class MyCustomTransport(JanusTransport):
    def __init__(self, base_url: str, **kwargs):
        super().__init__(base_url, **kwargs)
        # Initialize custom transport
    
    async def _connect(self) -> None:
        # Implement connection logic
        pass
    
    async def _disconnect(self) -> None:
        # Implement disconnection logic
        pass
    
    async def _send(self, message: Dict[str, Any]) -> None:
        # Implement message sending
        pass

# Register the custom transport
def protocol_matcher(base_url: str) -> bool:
    return base_url.startswith("mycustom://")

# Register with the transport system
JanusTransport.register_transport(MyCustomTransport)
```

## Error Handling

All transport implementations handle common error scenarios:

- **Connection failures**: Automatic retry with exponential backoff
- **Network timeouts**: Configurable timeout values
- **Protocol errors**: Proper error reporting and recovery
- **Server disconnections**: Automatic reconnection attempts

## Configuration Options

Transport classes accept various configuration options:

```python
session = JanusSession(
    base_url="wss://example.com/janus",
    # Transport-specific options
    timeout=30.0,           # Request timeout in seconds
    max_retries=3,          # Maximum retry attempts
    retry_delay=1.0,        # Initial retry delay
    keepalive_interval=30,  # Keepalive ping interval
)
```