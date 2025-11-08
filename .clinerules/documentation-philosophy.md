# Documentation Philosophy

## Keep It Simple

This project focuses on being **simple** and easy to use. The documentation should reflect this philosophy.

## Documentation Guidelines

### What to Document
- Basic usage examples
- Core functionality
- Essential setup instructions
- Common use cases

### What NOT to Document
- Advanced WebRTC configuration details
- Complex technical configurations that advanced users can discover themselves
- Implementation details that clutter the simple interface
- Edge cases that are not part of the core workflow

## Rationale

Advanced users who need complex configurations (like WebRTC peer connection settings, STUN/TURN server configuration, etc.) will:
1. Read the code and docstrings
2. Understand the underlying aiortc library
3. Find the configuration options through exploration
4. Not need hand-holding in the documentation

The documentation should serve the **majority use case** of users who want simple, straightforward WebRTC communication through Janus, not the minority who need advanced configuration.

## Examples

### ✅ Good Documentation
```python
# Simple plugin creation
plugin = JanusEchoTestPlugin()
await plugin.attach(session)
```

### ❌ Avoid in Documentation
```python
# Complex WebRTC configuration examples
config = RTCConfiguration(iceServers=[...])
plugin = JanusEchoTestPlugin(pc_config=config)
```

The advanced configuration capability exists in the code and is documented in docstrings, but doesn't need to be prominently featured in user-facing documentation.
