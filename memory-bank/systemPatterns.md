# System Patterns: Python Janus Client

## Architecture Overview

### High-Level Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    User Application                      │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                  JanusSession                            │
│  - Session lifecycle management                          │
│  - Plugin attachment/detachment                          │
│  - Message routing                                       │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
┌───────▼──────┐ ┌───▼────────┐ ┌─▼──────────┐
│   Plugins    │ │ Transport  │ │  Message   │
│              │ │  Layer     │ │Transaction │
│ - EchoTest   │ │            │ │            │
│ - VideoCall  │ │ - WebSocket│ │ - Tracking │
│ - VideoRoom  │ │ - HTTP     │ │ - Matching │
│ - TextRoom   │ │            │ │            │
└──────┬───────┘ └─────┬──────┘ └────────────┘
       │               │
┌──────▼───────────────▼──────┐
│      aiortc (WebRTC)        │
│  - RTCPeerConnection        │
│  - MediaStreamTrack         │
│  - JSEP handling            │
└─────────────────────────────┘
```

## Core Components

### 1. JanusSession
**Purpose:** Central session management and coordination

**Key Responsibilities:**
- Create/destroy Janus sessions
- Manage transport connection
- Route messages to plugins
- Handle keepalive
- Provide context manager interface

**Design Pattern:** Facade + Context Manager
```python
class JanusSession:
    async def __aenter__(self) -> "JanusSession"
    async def __aexit__(self, exc_type, exc_value, exc_tb) -> None
    async def attach_plugin(self, plugin: JanusPlugin) -> int
    async def send(self, message: dict, ...) -> dict
```

**Key Decisions:**
- Automatic connection on first use (lazy initialization)
- Context manager for automatic cleanup
- Single transport per session
- Plugin registry per session

### 2. Transport Layer
**Purpose:** Abstract communication protocols with Janus server

**Design Pattern:** Strategy Pattern + Factory
```python
class JanusTransport(ABC):
    async def _connect(self) -> None
    async def _disconnect(self) -> None
    async def _send(self, message: Dict) -> None
    async def receive(self, response: dict) -> None
```

**Implementations:**
- `JanusTransportWebsocket`: Full-duplex WebSocket communication
- `JanusTransportHTTP`: Long-polling HTTP communication

**Protocol Detection:**
```python
def protocol_matcher(base_url: str) -> bool:
    # WebSocket: ws:// or wss://
    # HTTP: http:// or https://
```

**Key Decisions:**
- Transport selected automatically from URL scheme
- Each transport handles its own message receiving
- Transports dispatch messages to sessions
- Session-to-transport mapping for HTTP long-polling

### 3. Plugin System
**Purpose:** Implement Janus plugin-specific functionality

**Design Pattern:** Template Method + Observer
```python
class JanusPlugin(ABC):
    async def attach(self, session: JanusSession) -> None
    async def destroy(self) -> None
    async def send(self, message: dict, ...) -> dict
    async def on_receive(self, response: dict) -> None
    async def on_receive_jsep(self, jsep: dict) -> None
```

**Plugin Hierarchy:**
```
JanusPlugin (Abstract Base)
├── JanusEchoTestPlugin
├── JanusVideoCallPlugin
├── JanusVideoRoomPlugin
└── JanusTextRoomPlugin
```

**Key Responsibilities:**
- Handle plugin-specific messages
- Manage WebRTC peer connections
- Process JSEP offers/answers
- Emit plugin-specific events

**Key Decisions:**
- Each plugin manages its own RTCPeerConnection
- Plugins receive filtered messages from session
- JSEP handling separated from regular messages
- Plugin state encapsulated within plugin instance

### 4. Message Transaction System
**Purpose:** Track request-response pairs and async message matching

**Design Pattern:** Promise/Future Pattern
```python
class MessageTransaction:
    def __init__(self) -> None
    async def get(self, matcher: dict, ...) -> dict
    async def done(self) -> None
```

**Key Features:**
- Unique transaction IDs for each request
- Async waiting for matching responses
- Timeout support
- Dictionary-based message matching
- Subset matching for flexible response handling

**Key Decisions:**
- Transaction ID auto-generated (UUID)
- Multiple transactions can be active simultaneously
- Transactions auto-cleanup on completion
- Support for both exact and subset matching

## Critical Implementation Patterns

### Pattern 1: Async Context Managers
**Used In:** JanusSession, Plugin lifecycle

**Purpose:** Automatic resource management
```python
async with JanusSession(base_url=url) as session:
    plugin = JanusEchoTestPlugin()
    await plugin.attach(session)
    try:
        # Use plugin
        pass
    finally:
        await plugin.destroy()
```

**Benefits:**
- Guaranteed cleanup
- Exception safety
- Clear resource lifecycle
- Pythonic API

### Pattern 2: Message Routing
**Used In:** Session → Plugin message dispatch

**Flow:**
```
Transport receives message
    ↓
Transport.receive() → Session.on_receive()
    ↓
Session routes to plugin based on handle_id
    ↓
Plugin.on_receive() or Plugin.on_receive_jsep()
```

**Key Decisions:**
- Session maintains plugin registry (handle_id → plugin)
- JSEP messages routed separately
- Unknown handles logged but don't crash
- Transaction system runs in parallel

### Pattern 3: WebRTC Peer Connection Management
**Used In:** All plugins with media

**Lifecycle:**
```
1. Create RTCPeerConnection
2. Add local tracks (if publishing)
3. Create offer/answer
4. Set local/remote descriptions
5. Handle ICE candidates (trickle or full)
6. Monitor connection state
7. Handle incoming tracks
8. Close connection on cleanup
```

**Key Decisions:**
- One peer connection per plugin instance
- Trickle ICE optional (can send all candidates at once)
- Track handlers set before connection establishment
- Graceful degradation on connection failures

### Pattern 4: Event-Driven Plugin Communication
**Used In:** TextRoom, VideoRoom for real-time events

**Pattern:**
```python
class JanusTextRoomPlugin:
    def on_event(self, event_type: TextRoomEventType, 
                 callback: Callable) -> None:
        self._event_handlers[event_type] = callback
    
    async def _trigger_event(self, event_type: TextRoomEventType, 
                            data: dict) -> None:
        if event_type in self._event_handlers:
            await self._event_handlers[event_type](data)
```

**Benefits:**
- Decoupled event handling
- User-defined callbacks
- Async event processing
- Type-safe event types (Enum)

### Pattern 5: Data Channel Communication
**Used In:** TextRoom plugin

**Flow:**
```
1. Setup WebRTC connection
2. Wait for data channel from Janus
3. Register channel handlers (open, close, message)
4. Send/receive text messages over channel
5. Handle channel lifecycle
```

**Key Decisions:**
- Data channel created by Janus (not client)
- Messages are JSON strings
- Separate from signaling channel
- Event-driven message handling

## Component Relationships

### Session ↔ Transport
- **Relationship:** One-to-one
- **Lifecycle:** Transport created with session, destroyed with session
- **Communication:** Session sends via transport, transport dispatches to session
- **Key Methods:**
  - `transport.create_session(session)` → session_id
  - `transport.send(message)` → response
  - `transport.receive(response)` → routes to session

### Session ↔ Plugin
- **Relationship:** One-to-many
- **Lifecycle:** Plugins attached to session, destroyed independently
- **Communication:** Bidirectional message passing
- **Key Methods:**
  - `session.attach_plugin(plugin)` → handle_id
  - `plugin.send(message)` → goes through session
  - `session.on_receive(response)` → routes to plugin

### Plugin ↔ WebRTC
- **Relationship:** One-to-one (per plugin instance)
- **Lifecycle:** RTCPeerConnection created when needed, closed on destroy
- **Communication:** JSEP signaling + media streams
- **Key Methods:**
  - `plugin.create_jsep(pc)` → offer/answer
  - `plugin.on_receive_jsep(jsep)` → process remote description
  - `pc.on("track")` → handle incoming media

## Error Handling Strategy

### Levels of Error Handling

1. **Transport Level**
   - Connection failures → retry or raise
   - Protocol errors → raise with context
   - Timeout errors → raise TimeoutError

2. **Session Level**
   - Session creation failure → raise PluginAttachFail
   - Message send failure → raise with transaction context
   - Keepalive failure → log warning, continue

3. **Plugin Level**
   - Attach failure → raise PluginAttachFail
   - Plugin-specific errors → raise custom exceptions
   - WebRTC errors → log and attempt recovery

4. **Application Level**
   - User handles exceptions from public API
   - Context managers ensure cleanup
   - Clear error messages with actionable information

### Error Recovery Patterns

**Connection Loss:**
- Transport detects disconnection
- Session notified
- Plugins notified
- User can recreate session

**Plugin Failure:**
- Plugin-specific error raised
- Plugin can be destroyed and recreated
- Session remains valid
- Other plugins unaffected

**WebRTC Failure:**
- Connection state monitored
- Failed state triggers cleanup
- User notified via exception
- Can retry with new plugin instance

## Performance Considerations

### Async Efficiency
- All I/O operations are async (no blocking)
- Concurrent message transactions
- Efficient event loop usage
- Minimal thread usage (aiortc uses threads internally)

### Memory Management
- Explicit cleanup via context managers
- Plugin destruction releases resources
- Media tracks properly closed
- No circular references

### Network Optimization
- WebSocket preferred for lower latency
- HTTP long-polling as fallback
- Trickle ICE reduces setup time
- Keepalive prevents connection drops

## Testing Patterns

### Unit Testing
- Mock transport for session tests
- Mock session for plugin tests
- Mock WebRTC components for media tests
- Pytest fixtures for common setups

### Integration Testing
- Real Janus server (or mock server)
- Full message flow testing
- WebRTC connection testing
- Error scenario testing

### Test Utilities
- `util.py`: Common test helpers
- Mock message generators
- Async test decorators
- Fixture factories

## Extension Points

### Adding New Plugins
1. Inherit from `JanusPlugin`
2. Implement `on_receive()` for plugin messages
3. Implement `on_receive_jsep()` if using WebRTC
4. Add plugin-specific methods
5. Export from `__init__.py`

### Adding New Transports
1. Inherit from `JanusTransport`
2. Implement `_connect()`, `_disconnect()`, `_send()`
3. Implement message receiving mechanism
4. Create `protocol_matcher()` function
5. Register with `register_transport()`

### Customizing Behavior
- Override plugin methods for custom logic
- Extend transport for custom protocols
- Hook into message transaction system
- Add custom event handlers
