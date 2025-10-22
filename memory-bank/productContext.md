# Product Context: Python Janus Client

## Why This Project Exists

### The Problem
WebRTC is a powerful technology for real-time communication, but it requires complex signaling infrastructure. Janus is a popular open-source WebRTC gateway that handles this complexity, but Python developers lacked a modern, async-first client library to interact with it.

**Specific Pain Points:**
- Existing Python WebRTC solutions were synchronous or incomplete
- No comprehensive Python client for Janus gateway
- Difficult to integrate WebRTC into Python applications
- Complex setup required for basic WebRTC functionality
- Limited examples and documentation for Python + Janus

### The Solution
python_janus_client provides a clean, async Python interface to Janus WebRTC gateway, leveraging modern Python features (async/await) and the robust aiortc library for WebRTC implementation.

**Key Benefits:**
- Simple API that hides WebRTC complexity
- Async/await for efficient I/O operations
- Built-in support for common Janus plugins
- Extensible architecture for custom needs
- Comprehensive examples and documentation

## How It Should Work

### User Experience Goals

#### 1. Simple Connection
Users should connect to Janus with minimal code:
```python
session = JanusSession(base_url="wss://janus.example.com/janus")
async with session:
    # Work with session
    pass
```

#### 2. Easy Plugin Usage
Attaching and using plugins should be intuitive:
```python
plugin = JanusEchoTestPlugin()
await plugin.attach(session)
await plugin.start("input.mp4", "output.mp4")
await plugin.destroy()
```

#### 3. Automatic Resource Management
- Connections auto-establish when needed
- Resources auto-cleanup with context managers
- No manual connection/disconnection required
- Graceful error handling

#### 4. Clear Media Handling
Media streaming should be straightforward:
```python
player = MediaPlayer("desktop", format="gdigrab")
recorder = MediaRecorder("output.mp4")
await plugin.call(username="user", player=player, recorder=recorder)
```

### Core Workflows

#### Workflow 1: Echo Test (Testing)
**Purpose:** Test WebRTC connectivity and media handling
**Steps:**
1. Create session
2. Attach EchoTest plugin
3. Start with input media source
4. Receive echoed media back
5. Record output
6. Cleanup

**Use Case:** Verify Janus server connectivity, test media pipeline

#### Workflow 2: Video Call (P2P Communication)
**Purpose:** Enable peer-to-peer video calls
**Steps:**
1. Create session
2. Attach VideoCall plugin
3. Register with username
4. Call another user OR wait for incoming call
5. Exchange media streams
6. Hangup when done
7. Cleanup

**Use Case:** Video conferencing, remote assistance, telemedicine

#### Workflow 3: Video Room (Multi-Party)
**Purpose:** Multi-party video conferencing
**Steps:**
1. Create session
2. Attach VideoRoom plugin
3. Join room (or create if needed)
4. Publish local media stream
5. Subscribe to other participants
6. Handle participant join/leave events
7. Leave room and cleanup

**Use Case:** Group video calls, webinars, virtual classrooms

#### Workflow 4: Text Room (Chat)
**Purpose:** Text-based chat rooms with data channels
**Steps:**
1. Create session
2. Attach TextRoom plugin
3. Setup WebRTC data channel
4. Join room
5. Send/receive text messages
6. Handle room events
7. Leave and cleanup

**Use Case:** Chat applications, real-time collaboration, signaling

### Design Philosophy

#### Async-First
- All I/O operations are async
- No blocking calls in the main path
- Efficient resource utilization
- Natural integration with async frameworks (FastAPI, aiohttp, etc.)

#### Minimal Dependencies
- Core dependencies: aiortc, websockets, aiohttp
- No unnecessary bloat
- Easy to install and deploy
- Reduced security surface

#### Extensibility
- Plugin base class for custom plugins
- Transport base class for custom protocols
- Hook points for customization
- Clear extension patterns

#### Developer-Friendly
- Type hints throughout
- Clear error messages
- Comprehensive examples
- Detailed documentation
- Follows Python conventions

## User Personas

### Persona 1: Application Developer
**Background:** Building a Python web application that needs video chat
**Needs:**
- Easy integration with existing async framework
- Reliable video/audio streaming
- Minimal setup complexity
- Good documentation

**Goals:**
- Add video chat feature quickly
- Maintain application performance
- Handle errors gracefully

### Persona 2: IoT Developer
**Background:** Building IoT devices that need WebRTC capabilities
**Needs:**
- Lightweight client
- Efficient resource usage
- Cross-platform support
- Stable API

**Goals:**
- Stream sensor data via WebRTC
- Remote device monitoring
- Low latency communication

### Persona 3: Researcher
**Background:** Researching WebRTC protocols and implementations
**Needs:**
- Access to low-level WebRTC details
- Ability to customize behavior
- Clear code structure
- Extensibility

**Goals:**
- Experiment with WebRTC features
- Implement custom protocols
- Analyze WebRTC performance

### Persona 4: Enterprise Developer
**Background:** Integrating with existing Janus deployment
**Needs:**
- Production-ready client
- Authentication support
- Admin API access
- Monitoring capabilities

**Goals:**
- Integrate with corporate infrastructure
- Manage Janus server programmatically
- Monitor system health

## Success Metrics

### Technical Metrics
- **Test Coverage:** >80% (currently at 82%)
- **API Stability:** Semantic versioning, backward compatibility
- **Performance:** Low latency, efficient resource usage
- **Reliability:** Graceful error handling, automatic recovery

### Adoption Metrics
- **PyPI Downloads:** Growing monthly downloads
- **GitHub Stars:** Community interest indicator
- **Issues/PRs:** Active community engagement
- **Documentation Views:** Usage indicator

### Quality Metrics
- **Bug Reports:** Low and decreasing
- **Response Time:** Quick issue resolution
- **Code Quality:** Clean, maintainable code
- **Documentation:** Complete and up-to-date

## Future Vision

### Short-Term (Next Release)
- Improve WebSocket cleanup
- Remove deprecation warnings
- Enhanced error messages
- More examples

### Medium-Term (6-12 months)
- Optional WebRTC dependency (signaling-only mode)
- Additional plugin support
- Performance optimizations
- Enhanced monitoring

### Long-Term (1+ years)
- Broader Janus feature coverage
- Advanced media processing
- Production-grade reliability
- Enterprise features
