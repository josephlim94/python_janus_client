# Session

Create a session object that can be shared between plugin handles.

The session is the main entry point for communicating with a Janus WebRTC Gateway server. It manages the connection, handles message routing, and provides lifecycle management for plugins.

## JanusSession

::: janus_client.session.JanusSession
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      docstring_section_style: table
      separate_signature: true
      show_signature_annotations: true

## PluginAttachFail Exception

::: janus_client.session.PluginAttachFail
    options:
      show_root_heading: true
      show_source: false
      docstring_section_style: table

## Usage Examples

### Basic Session Usage

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
            await plugin.start("input.mp4", "output.mp4")
            await asyncio.sleep(10)
            
            # Plugin will be automatically destroyed when session closes
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Manual Session Management

```python
import asyncio
from janus_client import JanusSession, JanusVideoRoomPlugin

async def main():
    session = JanusSession(base_url="https://example.com/janus")
    
    try:
        # Manually create session
        await session.create()
        
        # Attach plugin
        plugin = JanusVideoRoomPlugin()
        await plugin.attach(session)
        
        # Use plugin
        await plugin.join(room_id=1234, username="user1")
        
        # Manual cleanup
        await plugin.destroy()
        await session.destroy()
        
    except Exception as e:
        print(f"Error: {e}")
        # Ensure cleanup on error
        try:
            await session.destroy()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())
```

### Session with Custom Transport Options

```python
import asyncio
from janus_client import JanusSession

async def main():
    # Session with custom transport configuration
    session = JanusSession(
        base_url="wss://example.com/janus",
        timeout=30.0,           # Request timeout
        max_retries=3,          # Maximum retry attempts
        retry_delay=1.0,        # Initial retry delay
        keepalive_interval=30   # Keepalive ping interval
    )
    
    async with session:
        # Get server information
        info = await session.transport.info()
        print(f"Server info: {info}")
        
        # Send keepalive ping
        await session.keepalive()

if __name__ == "__main__":
    asyncio.run(main())
```

## Best Practices

### Always Use Context Managers

The recommended way to use sessions is with async context managers (`async with`), which ensures proper cleanup:

```python
async with session:
    # Your code here
    pass
# Session is automatically destroyed here
```

### Error Handling

Always wrap session operations in try-except blocks to handle connection failures:

```python
try:
    async with session:
        # Session operations
        pass
except ConnectionError:
    print("Failed to connect to Janus server")
except TimeoutError:
    print("Operation timed out")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Plugin Lifecycle

Plugins attached to a session should be properly destroyed:

```python
async with session:
    plugin = JanusEchoTestPlugin()
    try:
        await plugin.attach(session)
        # Use plugin
    finally:
        await plugin.destroy()  # Explicit cleanup
```

### Connection Reuse

Sessions can be reused for multiple operations, but should not be shared across different async tasks without proper synchronization:

```python
# Good: Sequential operations
async with session:
    plugin1 = JanusEchoTestPlugin()
    await plugin1.attach(session)
    await plugin1.start("input1.mp4")
    await plugin1.destroy()
    
    plugin2 = JanusVideoCallPlugin()
    await plugin2.attach(session)
    await plugin2.register("user1")
    await plugin2.destroy()

# Avoid: Concurrent access without synchronization
# Multiple plugins using the same session concurrently
# requires careful message handling
```
