# Session

Create a session object that can be shared between plugin handles

## Session Class

### `JanusSession`

The main session class for connecting to Janus WebRTC Gateway.

#### Constructor

```python
JanusSession(base_url: str, **kwargs)
```

**Parameters:**
- `base_url` (str): The base URL of the Janus server (e.g., "wss://example.com/janus" or "https://example.com/janus")
- `**kwargs`: Additional keyword arguments passed to the transport layer

#### Methods

##### `create()`

```python
async def create() -> Dict[str, Any]
```

Create a new session with the Janus server.

**Returns:**
- `Dict[str, Any]`: Response from Janus server containing session information

##### `destroy()`

```python
async def destroy() -> Dict[str, Any]
```

Destroy the session and clean up resources.

**Returns:**
- `Dict[str, Any]`: Response from Janus server confirming destruction

##### `send(message, timeout=None)`

```python
async def send(message: Dict[str, Any], timeout: Optional[float] = None) -> Dict[str, Any]
```

Send a message to the Janus server.

**Parameters:**
- `message` (Dict[str, Any]): The message to send
- `timeout` (Optional[float]): Timeout in seconds for the operation

**Returns:**
- `Dict[str, Any]`: Response from Janus server

##### `attach_plugin(plugin)`

```python
async def attach_plugin(plugin: JanusPlugin) -> Dict[str, Any]
```

Attach a plugin to this session.

**Parameters:**
- `plugin` (JanusPlugin): The plugin instance to attach

**Returns:**
- `Dict[str, Any]`: Response from Janus server containing plugin handle information

##### `detach_plugin(plugin)`

```python
async def detach_plugin(plugin: JanusPlugin) -> Dict[str, Any]
```

Detach a plugin from this session.

**Parameters:**
- `plugin` (JanusPlugin): The plugin instance to detach

**Returns:**
- `Dict[str, Any]`: Response from Janus server confirming detachment

## Usage Example

```python
import asyncio
from janus_client import JanusSession, JanusEchoTestPlugin

async def main():
    # Create session
    session = JanusSession(base_url="wss://example.com/janus")
    
    try:
        # Use session as async context manager for automatic cleanup
        async with session:
            # Create and attach plugin
            plugin = JanusEchoTestPlugin()
            await plugin.attach(session)
            
            # Use plugin...
            
            # Plugin will be automatically destroyed when session closes
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```
