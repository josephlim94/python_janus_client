# Cline Rules for Python Janus Client Project

## Project Overview

This is a Python async client library for the Janus WebRTC gateway. The project provides:
- WebRTC communication through aiortc
- Plugin-based architecture (EchoTest, VideoCall, VideoRoom)
- Multiple transport protocols (WebSocket, HTTP)
- Admin/Monitor API support
- Media streaming capabilities with PyAV

**Key Technologies:** Python 3.8-3.11, asyncio, aiortc, websockets, aiohttp, Poetry

## Python Development Standards

### Code Style & Formatting
- **Line Length:** 88 characters (matching project's Flake8 configuration)
- **Import Organization:** 
  - Standard library imports first
  - Third-party imports second
  - Local imports last
  - Use absolute imports for `janus_client` modules
- **String Quotes:** Use double quotes for strings, single quotes for string literals in code
- **Trailing Commas:** Use trailing commas in multi-line structures

### Type Hints
- **Required:** All public functions and methods must have type hints
- **Return Types:** Always specify return types, use `None` for procedures
- **Async Functions:** Use `async def` with proper return type annotations
- **Generics:** Use `typing` module generics (List, Dict, Optional, Union)
- **Example:**
```python
async def send_message(self, message: Dict[str, Any], timeout: Optional[float] = None) -> Dict[str, Any]:
    pass
```

### Async/Await Patterns
- **Prefer async/await:** Use async/await over callbacks
- **Context Managers:** Use async context managers for resource management
- **Error Handling:** Wrap async operations in try/except blocks
- **Timeouts:** Always specify timeouts for network operations
- **Example:**
```python
async with session:
    try:
        result = await plugin.send_message(msg, timeout=30.0)
    except asyncio.TimeoutError:
        logger.error("Operation timed out")
        raise
```

## Project Architecture Guidelines

### Plugin System
- **Base Class:** All plugins must inherit from `JanusPlugin`
- **Lifecycle:** Implement proper attach/destroy lifecycle
- **Message Handling:** Override `on_receive()` for plugin-specific messages
- **JSEP Handling:** Override `on_receive_jsep()` for WebRTC signaling
- **State Management:** Use internal state classes for complex plugins

### Transport Layer
- **Abstraction:** Use `JanusTransport` base class for new transports
- **Protocol Detection:** Implement `protocol_matcher()` function
- **Connection Management:** Handle connect/disconnect gracefully
- **Message Routing:** Properly route messages to sessions/plugins

### Session Management
- **Context Managers:** Use `async with` for session lifecycle
- **Plugin Attachment:** Attach plugins through session.attach_plugin()
- **Cleanup:** Always destroy sessions and plugins properly
- **Error Recovery:** Handle connection failures gracefully

## Code Organization Rules

### File Structure
```
janus_client/
├── __init__.py          # Public API exports
├── session.py           # Core session management
├── transport*.py        # Transport implementations
├── plugin_*.py          # Plugin implementations
├── admin_monitor.py     # Admin API client
├── media.py            # Media utilities
└── experiments/        # Experimental features
```

### Import Guidelines
- **Public API:** Only import necessary classes in `__init__.py`
- **Internal Imports:** Use relative imports within package
- **External Dependencies:** Import at module level, not in functions
- **Conditional Imports:** Use try/except for optional dependencies

### Dependency Management
- **Poetry:** Use `poetry add` for new dependencies
- **Version Constraints:** Use compatible version ranges (^1.0.0)
- **Dev Dependencies:** Separate development dependencies
- **Optional Dependencies:** Use extras for optional features

## Testing Standards

### Test Organization
```
test/
├── __init__.py
├── test_*.py           # Test modules matching source structure
└── util.py            # Test utilities and fixtures
```

### Test Patterns
- **Async Tests:** Use `pytest-asyncio` for async test functions
- **Fixtures:** Create reusable fixtures for sessions, plugins
- **Mocking:** Mock external dependencies (WebRTC, network calls)
- **Coverage:** Maintain >80% code coverage
- **Example:**
```python
@pytest.mark.asyncio
async def test_plugin_attach():
    session = await create_test_session()
    plugin = JanusEchoTestPlugin()
    
    await plugin.attach(session)
    assert plugin.id is not None
    
    await plugin.destroy()
```

### Mock Patterns
- **Transport Mocking:** Mock network calls for unit tests
- **WebRTC Mocking:** Mock aiortc components for plugin tests
- **Time Mocking:** Use `freezegun` for time-dependent tests

## Documentation Requirements

### Docstrings
- **Format:** Use Google-style docstrings exclusively
- **Required:** All public classes, methods, and functions must have docstrings
- **Conciseness:** Keep documentation as concise as possible while being clear
- **No Implementation Details:** Focus on what the function does, not how it does it
- **Parameters:** Document all parameters with types and brief descriptions
- **Returns:** Document return values and types
- **Raises:** Document exceptions that may be raised
- **Example:**
```python
async def join_room(self, room_id: int, username: str, pin: Optional[str] = None) -> bool:
    """Join a video room.
    
    Args:
        room_id: The ID of the room to join
        username: Username to use in the room
        pin: Optional room PIN for protected rooms
        
    Returns:
        True if successfully joined, False otherwise
        
    Raises:
        JanusError: If room doesn't exist or join fails
        TimeoutError: If operation times out
    """
```

### Documentation Style Guidelines
- **Concise Descriptions:** Use clear, brief descriptions that focus on purpose and behavior
- **Avoid Implementation Details:** Don't document internal algorithms, data structures, or implementation specifics
- **User-Focused:** Write from the perspective of someone using the API, not implementing it
- **Consistent Terminology:** Use consistent terms throughout the codebase
- **Examples:** Include usage examples for complex functions when helpful
- **Bad Example:** "This method iterates through the internal session dictionary and calls the transport's send method with a JSON-serialized message"
- **Good Example:** "Send a message to the Janus server and return a transaction for tracking the response"

### Code Comments
- **Complex Logic:** Comment complex algorithms or WebRTC-specific code
- **TODOs:** Use `# TODO:` for future improvements
- **Warnings:** Use `# WARNING:` for potential issues
- **References:** Include links to relevant RFCs or documentation

## Development Workflow

### Poetry Usage
- **Install:** `poetry install` for development setup
- **Dependencies:** `poetry add <package>` for new dependencies
- **Virtual Environment:** `poetry shell` to activate environment
- **Scripts:** Define common tasks in `pyproject.toml`

### Git Practices
- **Commits:** Use conventional commit messages
- **Branches:** Use feature branches for new development
- **Pull Requests:** Include tests and documentation updates
- **Versioning:** Follow semantic versioning (MAJOR.MINOR.PATCH)

### Code Quality
- **Linting:** Run `flake8` before committing
- **Testing:** Run full test suite with `pytest`
- **Coverage:** Check coverage with `coverage run -m pytest`
- **Type Checking:** Use `mypy` for static type checking

### Documentation Building
- **MkDocs Strict Mode:** Always use `--strict` flag when building documentation to catch warnings as errors
- **Build Command:** Use `poetry run python -W ignore::DeprecationWarning:mkdocs_autorefs -m mkdocs build --clean --strict`
- **Warning Suppression:** The command above suppresses known deprecation warnings from mkdocs-autorefs plugin
- **Local Testing:** Test documentation builds locally before committing changes
- **CI/CD:** The GitHub workflow automatically uses strict mode to ensure clean documentation builds

## WebRTC & Media Specific Guidelines

### aiortc Integration
- **Peer Connection:** Use `RTCPeerConnection` for WebRTC sessions
- **Media Tracks:** Handle `MediaStreamTrack` objects properly
- **JSEP Handling:** Process offer/answer/candidate messages correctly
- **Track Events:** Implement `on_track` handlers for incoming media
- **Example:**
```python
pc = RTCPeerConnection()

@pc.on("track")
async def on_track(track):
    if track.kind == "video":
        # Handle video track
        recorder.addTrack(track)
    elif track.kind == "audio":
        # Handle audio track
        recorder.addTrack(track)
```

### Media Handling
- **MediaPlayer:** Use for input media sources (files, devices, streams)
- **MediaRecorder:** Use for output media recording
- **Frame Processing:** Handle video/audio frames in custom tracks
- **Codec Support:** Be aware of supported codecs (H.264, VP8, Opus, etc.)
- **Resource Cleanup:** Always stop players and recorders properly

### Error Handling
- **Network Errors:** Handle connection failures gracefully
- **Media Errors:** Catch and handle media-related exceptions
- **Timeout Handling:** Use appropriate timeouts for all operations
- **Logging:** Use structured logging for debugging WebRTC issues

## Performance & Best Practices

### Async Optimization
- **Avoid Blocking:** Never use blocking I/O in async functions
- **Task Management:** Use `asyncio.create_task()` for concurrent operations
- **Resource Limits:** Set appropriate connection and timeout limits
- **Memory Management:** Clean up resources promptly

### Connection Management
- **Connection Pooling:** Reuse connections where possible
- **Graceful Shutdown:** Implement proper cleanup sequences
- **Reconnection Logic:** Handle temporary network failures
- **Health Checks:** Implement keepalive mechanisms

## Common Patterns & Examples

### Plugin Implementation Template
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

### Transport Implementation Template
```python
from janus_client import JanusTransport
from typing import Dict, Any

class MyCustomTransport(JanusTransport):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize transport-specific attributes
    
    async def _connect(self) -> None:
        """Establish connection to Janus server."""
        # Implement connection logic
        pass
    
    async def _disconnect(self) -> None:
        """Close connection to Janus server."""
        # Implement disconnection logic
        pass
    
    async def _send(self, message: Dict[str, Any]) -> None:
        """Send message to Janus server."""
        # Implement message sending
        pass

def protocol_matcher(base_url: str) -> bool:
    """Check if this transport can handle the URL."""
    return base_url.startswith("mycustom://")
```

### Session Usage Pattern
```python
async def example_session_usage():
    """Example of proper session and plugin usage."""
    session = JanusSession(base_url="wss://example.com/janus")
    
    try:
        # Use async context manager for automatic cleanup
        async with session:
            plugin = JanusEchoTestPlugin()
            await plugin.attach(session)
            
            try:
                # Perform plugin operations
                await plugin.start("input.mp4", "output.mp4")
                await asyncio.sleep(10)  # Let it run
                
            finally:
                # Always destroy plugin
                await plugin.destroy()
                
    except Exception as e:
        logger.error(f"Session error: {e}")
        raise
```

## Troubleshooting Guidelines

### Common Issues
- **Connection Timeouts:** Check network connectivity and server status
- **Plugin Attach Failures:** Verify plugin is available on server
- **Media Issues:** Check codec compatibility and media formats
- **Memory Leaks:** Ensure proper cleanup of sessions and plugins

### Debugging Tips
- **Enable Logging:** Use appropriate log levels for debugging
- **Network Inspection:** Monitor WebSocket/HTTP traffic
- **WebRTC Stats:** Use browser dev tools for WebRTC debugging
- **Performance Profiling:** Use Python profilers for performance issues

### Testing Strategies
- **Unit Tests:** Test individual components in isolation
- **Integration Tests:** Test full workflows with mock servers
- **Load Testing:** Test with multiple concurrent sessions
- **Error Injection:** Test error handling and recovery

## Security Considerations

### Authentication
- **API Keys:** Store securely, never commit to version control
- **Tokens:** Implement proper token refresh mechanisms
- **HTTPS/WSS:** Always use secure connections in production

### Input Validation
- **Message Validation:** Validate all incoming messages
- **Parameter Sanitization:** Sanitize user inputs
- **Rate Limiting:** Implement appropriate rate limits

### Resource Protection
- **Memory Limits:** Set appropriate memory limits
- **Connection Limits:** Limit concurrent connections
- **Timeout Protection:** Use timeouts to prevent resource exhaustion
