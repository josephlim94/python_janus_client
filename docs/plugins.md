# Plugins

Janus plugins provide specific functionality for different use cases. This library includes support for several core Janus plugins.

Plugins are the core components that implement specific WebRTC functionality. Each plugin corresponds to a server-side Janus plugin and provides a Python interface for interacting with it.

## Base Plugin Class

All plugins inherit from the base `JanusPlugin` class, which provides common functionality for plugin lifecycle management, message handling, and WebRTC signaling.

::: janus_client.plugin_base.JanusPlugin
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      docstring_section_style: table
      separate_signature: true
      show_signature_annotations: true

## EchoTest Plugin

The EchoTest plugin is useful for testing WebRTC connectivity. It echoes back any media sent to it, making it perfect for testing your setup.

::: janus_client.plugin_echotest.JanusEchoTestPlugin
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      docstring_section_style: table
      separate_signature: true
      show_signature_annotations: true

### EchoTest Usage Example

```python
import asyncio
from janus_client import JanusSession, JanusEchoTestPlugin

async def main():
    session = JanusSession(base_url="wss://example.com/janus")
    plugin = JanusEchoTestPlugin()
    
    async with session:
        await plugin.attach(session)
        
        # Start echo test with media files
        await plugin.start(input_file="input.mp4", output_file="echo_output.mp4")
        
        # Let it run for a while
        await asyncio.sleep(10)
        
        # Stop echo test
        await plugin.stop()
        await plugin.destroy()

if __name__ == "__main__":
    asyncio.run(main())
```

## VideoCall Plugin

The VideoCall plugin enables one-to-one video calls between users. It handles user registration, call initiation, and call management.

::: janus_client.plugin_video_call.JanusVideoCallPlugin
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      docstring_section_style: table
      separate_signature: true
      show_signature_annotations: true

### VideoCall Usage Example

```python
import asyncio
from janus_client import JanusSession, JanusVideoCallPlugin
from aiortc.contrib.media import MediaPlayer, MediaRecorder

async def main():
    session = JanusSession(base_url="wss://example.com/janus")
    plugin = JanusVideoCallPlugin()
    
    async with session:
        await plugin.attach(session)
        
        # Register with a username
        await plugin.register(username="caller")
        
        # Make a call
        player = MediaPlayer("input.mp4")
        recorder = MediaRecorder("output.mp4")
        await plugin.call(username="callee", player=player, recorder=recorder)
        
        # Wait for call duration
        await asyncio.sleep(30)
        
        # Hang up
        await plugin.hangup()
        await plugin.destroy()

if __name__ == "__main__":
    asyncio.run(main())
```

## VideoRoom Plugin

The VideoRoom plugin enables multi-party video conferencing. It supports room management, publishing, and subscribing to multiple video feeds.

::: janus_client.plugin_video_room.JanusVideoRoomPlugin
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      docstring_section_style: table
      separate_signature: true
      show_signature_annotations: true

### VideoRoom State Class

::: janus_client.plugin_video_room.JanusVideoRoomPlugin.State
    options:
      show_root_heading: true
      show_source: false
      docstring_section_style: table

### AllowedAction Enum

::: janus_client.plugin_video_room.AllowedAction
    options:
      show_root_heading: true
      show_source: false
      docstring_section_style: table

### VideoRoom Usage Example

```python
import asyncio
from janus_client import JanusSession, JanusVideoRoomPlugin
from aiortc.contrib.media import MediaPlayer, MediaRecorder

async def main():
    session = JanusSession(base_url="wss://example.com/janus")
    plugin = JanusVideoRoomPlugin()
    
    async with session:
        await plugin.attach(session)
        
        # Join a room
        await plugin.join(room_id=1234, username="user1")
        
        # Start publishing media
        player = MediaPlayer("video.mp4")
        await plugin.publish(player=player)
        
        # Subscribe to another participant's feed
        recorder = MediaRecorder("output.mp4")
        await plugin.subscribe_and_start(feed_id=5678, recorder=recorder)
        
        # Wait and then cleanup
        await asyncio.sleep(30)
        await plugin.unpublish()
        await plugin.unsubscribe()
        await plugin.leave()
        await plugin.destroy()

if __name__ == "__main__":
    asyncio.run(main())
```

## Plugin Development Guidelines

### Creating Custom Plugins

To create a custom plugin, inherit from `JanusPlugin` and implement the required methods:

```python
from janus_client import JanusPlugin
from typing import Dict, Any, Optional

class MyCustomPlugin(JanusPlugin):
    def __init__(self) -> None:
        super().__init__()
        self._state = {}
    
    async def on_receive(self, response: Dict[str, Any]) -> None:
        """Handle plugin-specific messages."""
        if "plugindata" in response:
            data = response["plugindata"]["data"]
            # Handle plugin data
            pass
    
    async def on_receive_jsep(self, jsep: Dict[str, Any]) -> None:
        """Handle WebRTC signaling."""
        if jsep["type"] == "offer":
            # Handle offer
            pass
        elif jsep["type"] == "answer":
            # Handle answer
            pass
    
    async def custom_action(self, param: str) -> bool:
        """Custom plugin action."""
        message = {"request": "custom", "param": param}
        response = await self.send(message)
        return response.get("success", False)
```

### Plugin Lifecycle

All plugins follow a standard lifecycle:

1. **Creation**: Instantiate the plugin class
2. **Attachment**: Attach to a session using `attach(session)`
3. **Usage**: Call plugin-specific methods
4. **Cleanup**: Destroy the plugin using `destroy()`

### Message Handling

Plugins receive two types of messages:

- **Plugin Messages**: Handled by `on_receive()` method
- **JSEP Messages**: WebRTC signaling handled by `on_receive_jsep()` method

### WebRTC Integration

Plugins that handle media use aiortc for WebRTC functionality:

- **MediaPlayer**: For input media (files, devices, streams)
- **MediaRecorder**: For output media recording
- **RTCPeerConnection**: For WebRTC peer connections
- **MediaStreamTrack**: For handling individual media tracks

## Best Practices

### Plugin Usage

1. **Always destroy plugins**: Use `await plugin.destroy()` when done
2. **Handle errors gracefully**: Wrap plugin operations in try-except blocks
3. **Use context managers**: Consider implementing `__aenter__` and `__aexit__` for custom plugins
4. **Check plugin state**: Verify plugin is attached before calling methods

### Media Handling

1. **Resource cleanup**: Always stop MediaPlayer and MediaRecorder instances
2. **Track management**: Handle track events properly in `on_track` callbacks
3. **Codec compatibility**: Ensure media formats are supported by Janus
4. **Performance**: Monitor memory usage with long-running media operations

### Error Handling

```python
async def safe_plugin_usage():
    session = JanusSession(base_url="wss://example.com/janus")
    plugin = JanusVideoRoomPlugin()
    
    try:
        async with session:
            await plugin.attach(session)
            
            # Plugin operations
            await plugin.join(room_id=1234, username="user1")
            
    except Exception as e:
        logger.error(f"Plugin error: {e}")
    finally:
        # Ensure cleanup
        try:
            await plugin.destroy()
        except:
            pass
```

### Concurrent Plugin Usage

When using multiple plugins with the same session, be careful about message routing:

```python
async def multiple_plugins():
    session = JanusSession(base_url="wss://example.com/janus")
    
    async with session:
        # Sequential plugin usage (recommended)
        plugin1 = JanusEchoTestPlugin()
        await plugin1.attach(session)
        await plugin1.start("input1.mp4")
        await plugin1.destroy()
        
        plugin2 = JanusVideoCallPlugin()
        await plugin2.attach(session)
        await plugin2.register("user1")
        await plugin2.destroy()
```
