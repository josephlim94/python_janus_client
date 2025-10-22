# Project Brief: Python Janus Client

## Project Identity
**Name:** python_janus_client (PyPI: janus-client)  
**Version:** 0.8.1  
**Type:** Python async client library  
**License:** MIT  
**Repository:** https://github.com/josephlim94/janus_gst_client_py

## Core Purpose
Provide a Python async client library for interacting with the Janus WebRTC gateway, enabling developers to easily send and share WebRTC media through Janus server.

## Key Requirements

### Functional Requirements
1. **WebRTC Communication**
   - Full WebRTC support using aiortc library
   - Media streaming (audio/video) capabilities
   - Peer connection management
   - JSEP (JavaScript Session Establishment Protocol) handling

2. **Plugin Support**
   - EchoTest plugin (media echo/loopback testing)
   - VideoCall plugin (peer-to-peer video calls)
   - VideoRoom plugin (multi-party video conferencing)
   - TextRoom plugin (text-based chat rooms with data channels)
   - Extensible plugin architecture for custom plugins

3. **Transport Protocols**
   - WebSocket transport
   - HTTP long-polling transport
   - Automatic protocol detection from URL
   - Extensible transport layer

4. **Authentication & Security**
   - Shared static secret (API key) support
   - Stored token authentication
   - Admin/Monitor API access

5. **Session Management**
   - Async context manager support
   - Automatic connection/disconnection
   - Session keepalive mechanisms
   - Plugin attachment/detachment

### Non-Functional Requirements
1. **Simplicity**
   - Simple, intuitive API
   - Minimal boilerplate code
   - Clear examples and documentation

2. **Performance**
   - Async/await throughout (no blocking operations)
   - Efficient media handling with PyAV
   - Proper resource cleanup

3. **Compatibility**
   - Python 3.8 through 3.13 support
   - Cross-platform (Windows, Linux, macOS)
   - Modern Python packaging standards

4. **Maintainability**
   - Clean code architecture
   - Comprehensive test coverage (target: >80%)
   - Type hints throughout
   - Clear documentation

5. **Extensibility**
   - Plugin base class for custom plugins
   - Transport base class for custom transports
   - Hook points for customization

## Project Scope

### In Scope
- Client-side Janus gateway interaction
- Core Janus plugins (EchoTest, VideoCall, VideoRoom, TextRoom)
- WebSocket and HTTP transports
- Admin/Monitor API client
- Media streaming utilities
- Comprehensive documentation
- Unit and integration tests

### Out of Scope
- Janus server implementation
- Browser-based client (this is Python-only)
- Custom codec implementations (relies on aiortc/PyAV)
- GUI/UI components
- Production-ready signaling server

### Experimental (Separate Folder)
- FFmpeg-based VideoRoom implementation
- GStreamer-based VideoRoom implementation
- Alternative media handling approaches

## Success Criteria
1. Successfully connect to Janus server via WebSocket or HTTP
2. Attach and use all core plugins
3. Send and receive WebRTC media streams
4. Maintain >80% test coverage
5. Clear, comprehensive documentation
6. Active PyPI package with regular updates
7. Stable API for production use

## Target Users
- Python developers building WebRTC applications
- Developers integrating with existing Janus deployments
- Teams building video conferencing solutions
- Researchers working with WebRTC technology
- IoT developers needing WebRTC capabilities

## Development Principles
1. **Async First:** All I/O operations use async/await
2. **Type Safety:** Comprehensive type hints
3. **Clean Code:** Follow Python best practices
4. **Test Coverage:** Maintain high test coverage
5. **Documentation:** Keep docs in sync with code
6. **Backward Compatibility:** Semantic versioning
7. **Modern Tooling:** Use Hatch for development workflow
