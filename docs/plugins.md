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

## TextRoom Plugin

The TextRoom plugin enables text-based communication through WebRTC DataChannels. It supports multiple rooms, public and private messaging, room management, and message history.

::: janus_client.plugin_textroom.JanusTextRoomPlugin
    options:
      show_root_heading: true
      show_source: false
      members_order: source
      docstring_section_style: table
      separate_signature: true
      show_signature_annotations: true

### TextRoomError Exception

::: janus_client.plugin_textroom.TextRoomError
    options:
      show_root_heading: true
      show_source: false
      docstring_section_style: table

### TextRoomEventType Enum

::: janus_client.plugin_textroom.TextRoomEventType
    options:
      show_root_heading: true
      show_source: false
      docstring_section_style: table

### TextRoom Usage Examples

#### Basic Room Communication

```python
import asyncio
from janus_client import JanusSession, JanusTextRoomPlugin, TextRoomEventType

async def main():
    session = JanusSession(base_url="wss://example.com/janus")
    plugin = JanusTextRoomPlugin()
    
    async with session:
        await plugin.attach(session)
        
        # Initialize WebRTC connection
        await plugin.setup()
        
        # Join a room
        participants = await plugin.join_room(
            room=1234,
            username="alice",
            display="Alice"
        )
        print(f"Joined room with {len(participants)} participants")
        
        # Register message handler
        def on_message(data):
            print(f"Message from {data['from']}: {data['text']}")
        
        plugin.on_event(TextRoomEventType.MESSAGE, on_message)
        
        # Send a public message
        await plugin.send_message(room=1234, text="Hello, everyone!")
        
        # Wait for messages
        await asyncio.sleep(10)
        
        # Leave the room
        await plugin.leave_room(room=1234)
        await plugin.destroy()

if __name__ == "__main__":
    asyncio.run(main())
```

#### Room Management

```python
import asyncio
from janus_client import JanusSession, JanusTextRoomPlugin

async def manage_rooms():
    session = JanusSession(base_url="wss://example.com/janus")
    plugin = JanusTextRoomPlugin()
    
    async with session:
        await plugin.attach(session)
        
        # List available rooms
        rooms = await plugin.list_rooms()
        print(f"Available rooms: {len(rooms)}")
        
        # Create a new room
        room_id = await plugin.create_room(
            description="My Chat Room",
            is_private=False,
            history=50,  # Store last 50 messages
            pin="1234"   # Require PIN to join
        )
        print(f"Created room: {room_id}")
        
        # List participants in a room
        participants = await plugin.list_participants(room=room_id)
        print(f"Participants: {participants}")
        
        # Destroy the room
        await plugin.destroy_room(room=room_id)
        await plugin.destroy()

if __name__ == "__main__":
    asyncio.run(manage_rooms())
```

#### Private Messaging

```python
import asyncio
from janus_client import JanusSession, JanusTextRoomPlugin, TextRoomEventType

async def private_messaging():
    # Create two sessions for two users
    session1 = JanusSession(base_url="wss://example.com/janus")
    plugin1 = JanusTextRoomPlugin()
    
    session2 = JanusSession(base_url="wss://example.com/janus")
    plugin2 = JanusTextRoomPlugin()
    
    async with session1, session2:
        # Setup both plugins
        await plugin1.attach(session1)
        await plugin1.setup()
        
        await plugin2.attach(session2)
        await plugin2.setup()
        
        # Create and join a room
        room_id = await plugin1.create_room(description="Private Chat")
        
        await plugin1.join_room(room=room_id, username="alice")
        await plugin2.join_room(room=room_id, username="bob")
        
        # Register message handler for bob
        def on_message(data):
            if data.get("whisper"):
                print(f"Private message from {data['from']}: {data['text']}")
            else:
                print(f"Public message from {data['from']}: {data['text']}")
        
        plugin2.on_event(TextRoomEventType.MESSAGE, on_message)
        
        # Alice sends private message to Bob
        await plugin1.send_message(
            room=room_id,
            text="Hi Bob, this is private!",
            to="bob"
        )
        
        # Alice sends message to multiple users
        await plugin1.send_message(
            room=room_id,
            text="Message to specific users",
            tos=["bob", "charlie"]
        )
        
        await asyncio.sleep(2)
        
        # Cleanup
        await plugin1.leave_room(room=room_id)
        await plugin2.leave_room(room=room_id)
        await plugin1.destroy_room(room=room_id)
        await plugin1.destroy()
        await plugin2.destroy()

if __name__ == "__main__":
    asyncio.run(private_messaging())
```

#### Event Handling

```python
import asyncio
from janus_client import JanusSession, JanusTextRoomPlugin, TextRoomEventType

async def handle_events():
    session = JanusSession(base_url="wss://example.com/janus")
    plugin = JanusTextRoomPlugin()
    
    async with session:
        await plugin.attach(session)
        await plugin.setup()
        
        # Register event handlers
        def on_join(data):
            print(f"User {data['username']} joined the room")
        
        def on_leave(data):
            print(f"User {data['username']} left the room")
        
        def on_message(data):
            print(f"Message from {data['from']}: {data['text']}")
        
        def on_kicked(data):
            print(f"User {data['username']} was kicked")
        
        def on_destroyed(data):
            print(f"Room {data['room']} was destroyed")
        
        def on_announcement(data):
            print(f"Announcement: {data['text']}")
        
        def on_error(data):
            print(f"Error: {data.get('error', 'Unknown error')}")
        
        plugin.on_event(TextRoomEventType.JOIN, on_join)
        plugin.on_event(TextRoomEventType.LEAVE, on_leave)
        plugin.on_event(TextRoomEventType.MESSAGE, on_message)
        plugin.on_event(TextRoomEventType.KICKED, on_kicked)
        plugin.on_event(TextRoomEventType.DESTROYED, on_destroyed)
        plugin.on_event(TextRoomEventType.ANNOUNCEMENT, on_announcement)
        plugin.on_event(TextRoomEventType.ERROR, on_error)
        
        # Create and join room
        room_id = await plugin.create_room(description="Event Demo")
        await plugin.join_room(room=room_id, username="alice")
        
        # Send a message
        await plugin.send_message(room=room_id, text="Hello!")
        
        # Wait for events
        await asyncio.sleep(5)
        
        # Cleanup
        await plugin.leave_room(room=room_id)
        await plugin.destroy_room(room=room_id)
        await plugin.destroy()

if __name__ == "__main__":
    asyncio.run(handle_events())
```

#### Message History

```python
import asyncio
from janus_client import JanusSession, JanusTextRoomPlugin, TextRoomEventType

async def message_history():
    session = JanusSession(base_url="wss://example.com/janus")
    plugin = JanusTextRoomPlugin()
    
    async with session:
        await plugin.attach(session)
        await plugin.setup()
        
        # Create room with message history
        room_id = await plugin.create_room(
            description="History Room",
            history=100  # Store last 100 messages
        )
        
        # Join and send some messages
        await plugin.join_room(room=room_id, username="alice")
        
        for i in range(5):
            await plugin.send_message(
                room=room_id,
                text=f"Message {i+1}"
            )
        
        # Leave the room
        await plugin.leave_room(room=room_id)
        
        # Track history messages
        history_messages = []
        
        def on_message(data):
            history_messages.append(data)
            print(f"History: {data['text']}")
        
        plugin.on_event(TextRoomEventType.MESSAGE, on_message)
        
        # Rejoin with history enabled
        await plugin.join_room(
            room=room_id,
            username="alice",
            history=True
        )
        
        # Wait for history to be delivered
        await asyncio.sleep(2)
        
        print(f"Received {len(history_messages)} messages from history")
        
        # Cleanup
        await plugin.leave_room(room=room_id)
        await plugin.destroy_room(room=room_id)
        await plugin.destroy()

if __name__ == "__main__":
    asyncio.run(message_history())
```

#### Room Administration

```python
import asyncio
from janus_client import JanusSession, JanusTextRoomPlugin

async def room_administration():
    session = JanusSession(base_url="wss://example.com/janus")
    plugin = JanusTextRoomPlugin()
    
    async with session:
        await plugin.attach(session)
        await plugin.setup()
        
        # Create room with secret for admin operations
        room_id = await plugin.create_room(
            description="Moderated Room",
            secret="admin_secret",
            is_private=False
        )
        
        await plugin.join_room(room=room_id, username="moderator")
        
        # Send announcement (requires secret)
        await plugin.send_announcement(
            room=room_id,
            text="Welcome to the moderated room!",
            secret="admin_secret"
        )
        
        # Kick a participant (requires secret)
        # await plugin.kick_participant(
        #     room=room_id,
        #     username="troublemaker",
        #     secret="admin_secret"
        # )
        
        # Cleanup
        await plugin.leave_room(room=room_id)
        await plugin.destroy_room(room=room_id, secret="admin_secret")
        await plugin.destroy()

if __name__ == "__main__":
    asyncio.run(room_administration())
```

### TextRoom Features

#### Room Configuration

- **Room ID**: Auto-generated or manually specified
- **Description**: Human-readable room description
- **PIN Protection**: Optional PIN required to join
- **Private Rooms**: Hidden from room listings
- **Message History**: Configurable number of messages to store
- **HTTP Backend**: Forward messages to external HTTP endpoint
- **Permanent Rooms**: Save room configuration to server config file

#### Messaging Features

- **Public Messages**: Broadcast to all room participants
- **Private Messages**: Send to specific user(s)
- **Announcements**: Admin-only broadcasts
- **Message Acknowledgment**: Optional confirmation of message delivery
- **Message History**: Retrieve past messages when joining

#### Event System

The plugin provides event handlers for:

- **JOIN**: User joins the room
- **LEAVE**: User leaves the room
- **MESSAGE**: New message received
- **KICKED**: User was kicked from room
- **DESTROYED**: Room was destroyed
- **ANNOUNCEMENT**: Admin announcement received
- **ERROR**: Error occurred

### TextRoom Best Practices

#### Connection Management

```python
# Always setup before joining rooms
await plugin.setup(timeout=30.0)

# Wait for setup to complete before operations
await plugin.join_room(room=1234, username="user")
```

#### Error Handling

```python
from janus_client import TextRoomError

try:
    await plugin.join_room(room=1234, username="alice", pin="1234")
except TextRoomError as e:
    print(f"Failed to join room: {e.error_message} (code: {e.error_code})")
```

#### Resource Cleanup

```python
try:
    # Use the plugin
    await plugin.join_room(room=1234, username="alice")
    await plugin.send_message(room=1234, text="Hello!")
finally:
    # Always cleanup
    try:
        await plugin.leave_room(room=1234)
    except:
        pass
    await plugin.destroy()
```

#### Event Handler Registration

```python
# Register handlers before joining rooms
plugin.on_event(TextRoomEventType.MESSAGE, on_message)
plugin.on_event(TextRoomEventType.JOIN, on_join)

# Then join the room
await plugin.join_room(room=1234, username="alice")
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
