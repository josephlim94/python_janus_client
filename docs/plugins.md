# Plugins

Janus plugins provide specific functionality for different use cases. This library includes support for several core Janus plugins.

## VideoRoom Plugin

### `JanusVideoRoomPlugin`

Plugin for multi-party video conferencing using Janus VideoRoom plugin.

#### Methods

##### `join_room(room_id, username, pin=None)`

```python
async def join_room(room_id: int, username: str, pin: Optional[str] = None) -> Dict[str, Any]
```

Join a video room.

**Parameters:**
- `room_id` (int): The ID of the room to join
- `username` (str): Username to use in the room
- `pin` (Optional[str]): Optional room PIN for protected rooms

**Returns:**
- `Dict[str, Any]`: Response from Janus server

##### `leave_room()`

```python
async def leave_room() -> Dict[str, Any]
```

Leave the current video room.

**Returns:**
- `Dict[str, Any]`: Response from Janus server

##### `publish(player)`

```python
async def publish(player: MediaPlayer) -> Dict[str, Any]
```

Start publishing media to the room.

**Parameters:**
- `player` (MediaPlayer): Media player instance for input media

**Returns:**
- `Dict[str, Any]`: Response from Janus server

##### `unpublish()`

```python
async def unpublish() -> Dict[str, Any]
```

Stop publishing media to the room.

**Returns:**
- `Dict[str, Any]`: Response from Janus server

##### `subscribe(feed_id, recorder=None)`

```python
async def subscribe(feed_id: int, recorder: Optional[MediaRecorder] = None) -> Dict[str, Any]
```

Subscribe to a publisher's media feed.

**Parameters:**
- `feed_id` (int): The feed ID to subscribe to
- `recorder` (Optional[MediaRecorder]): Optional recorder for saving received media

**Returns:**
- `Dict[str, Any]`: Response from Janus server

##### `unsubscribe()`

```python
async def unsubscribe() -> Dict[str, Any]
```

Unsubscribe from the current media feed.

**Returns:**
- `Dict[str, Any]`: Response from Janus server

#### Usage Example

```python
import asyncio
from janus_client import JanusSession, JanusVideoRoomPlugin
from aiortc.contrib.media import MediaPlayer, MediaRecorder

async def main():
    session = JanusSession(base_url="wss://example.com/janus")
    plugin = JanusVideoRoomPlugin()
    
    async with session:
        await plugin.attach(session)
        
        # Join room
        await plugin.join_room(room_id=1234, username="user1")
        
        # Start publishing
        player = MediaPlayer("video.mp4")
        await plugin.publish(player)
        
        # Subscribe to another feed
        recorder = MediaRecorder("output.mp4")
        await plugin.subscribe(feed_id=5678, recorder=recorder)
        
        # Wait and then cleanup
        await asyncio.sleep(30)
        await plugin.unpublish()
        await plugin.leave_room()
        await plugin.destroy()

if __name__ == "__main__":
    asyncio.run(main())
```

## VideoCall Plugin

### `JanusVideoCallPlugin`

Plugin for one-to-one video calls using Janus VideoCall plugin.

#### Methods

##### `register(username)`

```python
async def register(username: str) -> Dict[str, Any]
```

Register with the VideoCall plugin using a username.

**Parameters:**
- `username` (str): Username to register with

**Returns:**
- `Dict[str, Any]`: Response from Janus server

##### `call(username, player=None, recorder=None)`

```python
async def call(username: str, player: Optional[MediaPlayer] = None, recorder: Optional[MediaRecorder] = None) -> Dict[str, Any]
```

Make a call to another user.

**Parameters:**
- `username` (str): Username of the user to call
- `player` (Optional[MediaPlayer]): Media player for outgoing media
- `recorder` (Optional[MediaRecorder]): Media recorder for incoming media

**Returns:**
- `Dict[str, Any]`: Response from Janus server

##### `accept(player=None, recorder=None)`

```python
async def accept(player: Optional[MediaPlayer] = None, recorder: Optional[MediaRecorder] = None) -> Dict[str, Any]
```

Accept an incoming call.

**Parameters:**
- `player` (Optional[MediaPlayer]): Media player for outgoing media
- `recorder` (Optional[MediaRecorder]): Media recorder for incoming media

**Returns:**
- `Dict[str, Any]`: Response from Janus server

##### `hangup()`

```python
async def hangup() -> Dict[str, Any]
```

Hang up the current call.

**Returns:**
- `Dict[str, Any]`: Response from Janus server

#### Usage Example

```python
import asyncio
from janus_client import JanusSession, JanusVideoCallPlugin
from aiortc.contrib.media import MediaPlayer, MediaRecorder

async def main():
    session = JanusSession(base_url="wss://example.com/janus")
    plugin = JanusVideoCallPlugin()
    
    async with session:
        await plugin.attach(session)
        
        # Register
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

## EchoTest Plugin

### `JanusEchoTestPlugin`

Plugin for testing WebRTC connectivity using Janus EchoTest plugin.

#### Methods

##### `start(input_file=None, output_file=None)`

```python
async def start(input_file: Optional[str] = None, output_file: Optional[str] = None) -> Dict[str, Any]
```

Start the echo test.

**Parameters:**
- `input_file` (Optional[str]): Path to input media file
- `output_file` (Optional[str]): Path to save output media

**Returns:**
- `Dict[str, Any]`: Response from Janus server

##### `stop()`

```python
async def stop() -> Dict[str, Any]
```

Stop the echo test.

**Returns:**
- `Dict[str, Any]`: Response from Janus server

#### Usage Example

```python
import asyncio
from janus_client import JanusSession, JanusEchoTestPlugin

async def main():
    session = JanusSession(base_url="wss://example.com/janus")
    plugin = JanusEchoTestPlugin()
    
    async with session:
        await plugin.attach(session)
        
        # Start echo test
        await plugin.start(input_file="input.mp4", output_file="echo_output.mp4")
        
        # Let it run for a while
        await asyncio.sleep(10)
        
        # Stop echo test
        await plugin.stop()
        await plugin.destroy()

if __name__ == "__main__":
    asyncio.run(main())
```

## Base Class

### `JanusPlugin`

Base class for all Janus plugins. All plugin implementations inherit from this class.

#### Methods

##### `attach(session)`

```python
async def attach(session: JanusSession) -> Dict[str, Any]
```

Attach this plugin to a Janus session.

**Parameters:**
- `session` (JanusSession): The session to attach to

**Returns:**
- `Dict[str, Any]`: Response from Janus server

##### `destroy()`

```python
async def destroy() -> Dict[str, Any]
```

Destroy the plugin handle and clean up resources.

**Returns:**
- `Dict[str, Any]`: Response from Janus server

##### `send(message, jsep=None)`

```python
async def send(message: Dict[str, Any], jsep: Optional[Dict[str, Any]] = None) -> Dict[str, Any]
```

Send a message to the plugin.

**Parameters:**
- `message` (Dict[str, Any]): The message to send
- `jsep` (Optional[Dict[str, Any]]): Optional JSEP (WebRTC signaling) data

**Returns:**
- `Dict[str, Any]`: Response from Janus server

##### `trickle(candidate)`

```python
async def trickle(candidate: Dict[str, Any]) -> Dict[str, Any]
```

Send an ICE candidate to the plugin.

**Parameters:**
- `candidate` (Dict[str, Any]): ICE candidate data

**Returns:**
- `Dict[str, Any]`: Response from Janus server

#### Properties

- `id` (Optional[int]): The plugin handle ID assigned by Janus
- `session` (Optional[JanusSession]): The session this plugin is attached to
