# Testing Guidelines for Python Janus Client

## Test Execution Commands

### Basic Test Execution

**Run all tests across all Python environments:**
```bash
hatch test
```

**Run tests on specific Python version:**
```bash
hatch test -i py=3.8
```

**Run tests with verbose output:**
```bash
hatch test -- -v
```

**Run tests with full output and logging:**
```bash
hatch test -- -s --log-cli-level=INFO --full-trace
```

### Specific Test Execution

**Run specific test file:**
```bash
hatch test tests/test_plugin_textroom.py
hatch test .\tests\test_plugin.py  # Windows path format
```

**Run specific test class:**
```bash
hatch test tests/test_plugin_textroom.py::TestTransportHttp
```

**Run specific test method:**
```bash
hatch test tests/test_plugin_textroom.py::TestTransportHttp::test_textroom_join
hatch test .\tests\test_plugin.py::TestTransportHttp::test_plugin_echotest_create
```

**Run specific test with full logging on specific Python version:**
```bash
hatch test -i py=3.8 .\tests\test_plugin.py::TestTransportHttp::test_plugin_echotest_create -- -s --log-cli-level=INFO --full-trace
```

### Coverage Testing

**Run tests with coverage:**
```bash
hatch test -c
hatch test -i py=3.8 -c  # Specific Python version
```

**Generate HTML coverage report:**
```bash
hatch test -i py=3.8 -c
hatch env run -e py3.8 coverage html
```

**Coverage target:** Maintain >80% code coverage (currently 82%)

## Test Organization

### Test Structure
```
tests/
├── __init__.py
├── conftest.py              # Pytest configuration and fixtures
├── util.py                  # Test utilities
├── test_plugin.py           # Plugin base tests
├── test_plugin_echotest.py  # EchoTest plugin tests
├── test_plugin_video_call.py
├── test_plugin_video_room.py
├── test_plugin_textroom.py
├── test_transport.py        # Transport layer tests
├── test_admin.py            # Admin API tests
└── test_*.py               # Other test modules
```

### Test Patterns

**Async test decorator:**
```python
import pytest
from tests.util import async_test

@async_test
async def test_something():
    # Test implementation
    pass
```

**Standard pytest async:**
```python
@pytest.mark.asyncio
async def test_plugin_attach():
    session = JanusSession(base_url="wss://example.com/janus")
    plugin = JanusEchoTestPlugin()
    
    async with session:
        await plugin.attach(session)
        assert plugin.id is not None
        await plugin.destroy()
```

## Test Environment Setup

### Environment Variables for Testing
- **JANUS_HTTP_URL:** HTTP transport URL for tests
- **JANUS_WS_URL:** WebSocket transport URL for tests
- **JANUS_HTTP_BASE_PATH:** Base path for HTTP tests
- **JANUS_API_SECRET:** API secret for authenticated tests

### Test Server Requirements
- Janus server with EchoTest, VideoCall, VideoRoom, TextRoom plugins enabled
- WebSocket and HTTP transports enabled
- API key authentication configured (optional)

## Integration Test Characteristics

### WebRTC Tests
- **Duration:** 20-25 seconds each for WebRTC setup
- **Expected logs:** Look for "Track audio received" and "Track video received"
- **ICE connection:** Should show "ICE completed"
- **Flakiness:** Occasional failures due to network timing (acceptable)

### Plugin Base Tests
- **Count:** 4 tests total
- **Coverage:** EchoTest plugin with full WebRTC handshake
- **Transports:** Both HTTP and WebSocket tested
- **Media:** Audio and video track handling verified

## Test Execution Best Practices

### Development Testing
```bash
# Quick test during development
hatch test -i py=3.8 tests/test_plugin_textroom.py -- -v

# Full test with logging for debugging
hatch test -i py=3.8 tests/test_plugin_textroom.py::TestTransportHttp::test_textroom_join -- -s --log-cli-level=INFO --full-trace
```

### Pre-commit Testing
```bash
# Run all tests on default Python version
hatch test -i py=3.8

# Check coverage
hatch test -i py=3.8 -c

# Full test suite (takes longer)
hatch test
```

### CI/CD Testing
```bash
# Full test suite across all Python versions
hatch test

# Coverage report
hatch test -i py=3.8 -c
hatch env run -e py3.8 coverage html
```

## Test Troubleshooting

### Common Issues

**"pytest not recognized" error:**
- Use `hatch test` instead of direct pytest
- Ensure you're in the project directory

**"Unknown environment: test" error:**
- Use `hatch test` (not `hatch run test:pytest`)
- Check hatch configuration in pyproject.toml

**WebRTC connection failures:**
- Check Janus server is running and accessible
- Verify firewall settings
- Check STUN/TURN server configuration
- Review aiortc logs for details

**Import errors in tests:**
```bash
# Clean and recreate environment
hatch env prune
hatch env create

# Verify installation
hatch run python -c "import janus_client; print('OK')"
```

### Test Flakiness
- **Cause:** Network timing, server availability
- **Acceptable:** For integration tests with real WebRTC connections
- **Workaround:** Retry failed tests, use longer timeouts
- **Not acceptable:** For unit tests (should be deterministic)

## Test Coverage Guidelines

### Coverage Configuration
- **File:** .coveragerc
- **Target:** >80% coverage
- **Current:** 82%
- **Exclusions:** Test files, experimental code

### Coverage Commands
```bash
# Run with coverage
hatch test -i py=3.8 -c

# Generate HTML report
hatch env run -e py3.8 coverage html

# View coverage report
# Open htmlcov/index.html in browser
```

### Coverage Interpretation
- **High priority:** Core functionality (session, transport, plugins)
- **Medium priority:** Admin API, utilities
- **Low priority:** Experimental features, examples

## Test Data and Fixtures

### Test Fixtures (conftest.py)
- Session fixtures for different transports
- Mock server responses
- Media file fixtures
- Configuration fixtures

### Test Utilities (util.py)
- `async_test` decorator
- Helper functions for test setup
- Mock implementations
- Test data generators

## Performance Testing

### Load Testing (Manual)
```bash
# Run multiple concurrent sessions
# Monitor memory usage
# Check connection cleanup
# Verify no resource leaks
```

### Benchmarking
- Not currently automated
- Manual testing for performance regressions
- Focus on connection setup time
- Monitor memory usage patterns

## Test Maintenance

### Adding New Tests
1. Follow existing patterns in test files
2. Use appropriate fixtures from conftest.py
3. Add async_test decorator for async tests
4. Include both positive and negative test cases
5. Update coverage expectations if needed

### Updating Tests
1. Run tests before making changes
2. Update tests to match API changes
3. Ensure coverage doesn't decrease
4. Test both HTTP and WebSocket transports
5. Verify integration tests still pass

### Test Review Checklist
- [ ] Tests cover both success and failure cases
- [ ] Async tests use proper decorators
- [ ] Integration tests have reasonable timeouts
- [ ] Mock objects are used appropriately
- [ ] Test names are descriptive
- [ ] Coverage target is maintained
