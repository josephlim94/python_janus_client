# Active Context: Python Janus Client

## Current Focus

### Primary Task: Memory Bank Initialization
**Status:** In Progress  
**Started:** 2025-10-22  
**Goal:** Create comprehensive Cline Memory Bank for project continuity

**Completed:**
- ✅ Created memory-bank directory structure
- ✅ Wrote projectbrief.md (foundation document)
- ✅ Wrote productContext.md (why and how)
- ✅ Wrote systemPatterns.md (architecture)
- ✅ Wrote techContext.md (technical setup)
- 🔄 Writing activeContext.md (current state)
- ⏳ Need to write progress.md (project status)

## Recent Work

### WebRTC Capabilities Enhancement
**Status:** Completed (v0.8.2+)  
**Started:** 2025-11-08  
**Goal:** Fully expose WebRTC capabilities from plugin base while enforcing single peer connection per plugin

**Key Features:**
- Direct access to `RTCPeerConnection` via `pc` property
- Single peer connection constraint enforced per plugin instance
- Full aiortc API exposure without wrapper methods
- Proper connection lifecycle management with `reset_connection()`
- Comprehensive documentation of limitations

**Files Modified:**
- `janus_client/plugin_base.py` - Enhanced with `pc` property and `reset_connection()`
- `janus_client/plugin_echotest.py` - Updated to use base class PC exclusively
- Removed duplicate `on_receive_jsep()` implementation from EchoTest

**Key Decisions:**
- Expose `RTCPeerConnection` directly rather than wrapping API methods
- Initialize PC in constructor for predictable behavior
- Use `reset_connection()` for legitimate reconnection scenarios
- Document single PC limitation clearly in class docstrings

**Test Results:**
- ✅ All 4 plugin base unit tests passed (47.06s total)
- ✅ HTTP transport EchoTest: Full WebRTC handshake successful
- ✅ WebSocket transport EchoTest: Full WebRTC handshake successful
- ✅ Plugin creation failure test: Proper error handling verified
- ✅ Media streaming: Audio and video tracks received successfully
- ✅ ICE negotiation: Connection establishment working correctly

### TextRoom Plugin Development
**Status:** Completed (v0.8.1)  
**Key Features:**
- WebRTC data channel communication
- Room management (create, destroy, list)
- Participant management (join, leave, kick)
- Message sending (private, public, announcements)
- Event-driven architecture with callbacks
- Comprehensive error handling

**Files Modified:**
- `janus_client/plugin_textroom.py` - Main implementation
- `tests/test_plugin_textroom.py` - Test suite
- `docs/plugins.md` - Documentation

**Key Decisions:**
- Used data channels instead of WebSocket for messages
- Event-driven callbacks for real-time updates
- Enum-based event types for type safety
- Separate setup phase for WebRTC connection

### Migration from Poetry to Hatch
**Status:** Completed  
**Impact:** Development workflow changed  
**Benefits:**
- Better PEP 517/518 compliance
- Simpler configuration
- Integrated testing across Python versions
- Modern tooling

**Breaking Changes:** None for end users, only developer workflow

## Active Decisions & Considerations

### 1. WebSocket Cleanup Issue
**Problem:** WebSocket connections don't clean up properly in some scenarios  
**Impact:** Resource leaks in long-running applications  
**Priority:** Medium  
**Next Steps:**
- Investigate connection lifecycle
- Add proper cleanup handlers
- Test with long-running sessions
- Document workarounds if needed

### 2. Deprecation Warnings
**Problem:** Some dependencies emit deprecation warnings  
**Source:** Primarily from mkdocs-autorefs  
**Impact:** Low (warnings only, no functional issues)  
**Current Workaround:** Suppress in documentation build  
**Next Steps:**
- Monitor dependency updates
- Update when fixes available
- Consider alternatives if needed

### 3. Optional WebRTC Dependency
**Idea:** Make aiortc optional for signaling-only use cases  
**Benefit:** Lighter installation for apps that only need signaling  
**Challenge:** Significant refactoring required  
**Priority:** Low (future enhancement)  
**Considerations:**
- Maintain backward compatibility
- Clear documentation on when WebRTC is needed
- Separate plugin implementations?

## Important Patterns & Preferences

### Code Organization
- **Plugin pattern:** Each plugin is self-contained with clear lifecycle
- **Async-first:** All I/O operations use async/await
- **Context managers:** Preferred for resource management
- **Type hints:** Required for all public APIs
- **Error handling:** Specific exceptions with clear messages

### Testing Approach
- **Integration tests:** Test against real Janus server when possible
- **Mocking:** Mock transport and WebRTC for unit tests
- **Coverage:** Maintain >80% coverage
- **Async tests:** Use pytest-asyncio markers
- **Fixtures:** Reusable test fixtures in conftest.py

### Documentation Style
- **Google-style docstrings:** Consistent format
- **Concise:** Brief but complete
- **Examples:** Include working code examples
- **Auto-generation:** Use mkdocstrings for API docs
- **Strict mode:** Always build docs with --strict flag

### Development Workflow
1. Make changes in feature branch
2. Run tests locally: `hatch test -i py=3.8`
3. Check coverage: `hatch test -i py=3.8 -c`
4. Build docs: `hatch run docs-build`
5. Commit with clear message
6. Create PR with description

### Unit Test Execution
**Full Test Suite:**
```bash
hatch test  # Run all tests across all Python environments
```

**Specific Test Files:**
```bash
# Run all plugin base tests (includes EchoTest)
hatch test .\tests\test_plugin.py -- -s --log-cli-level=INFO --full-trace

# Run specific test method
hatch test .\tests\test_plugin.py::TestTransportHttp::test_plugin_echotest_create -- -s --log-cli-level=INFO --full-trace
hatch test .\tests\test_plugin.py::TestTransportWebsocket::test_plugin_echotest_create -- -s --log-cli-level=INFO --full-trace
```

**Test Environment Options:**
```bash
hatch test -i py=3.8  # Run on specific Python version
hatch test -c         # Run with coverage
hatch test -- -v      # Verbose output
```

**Test Results Interpretation:**
- All plugin base tests should pass (4/4 tests)
- EchoTest tests verify full WebRTC handshake
- Look for "Track audio received" and "Track video received" in logs
- ICE connection establishment should show "ICE completed"
- Tests typically take 20-25 seconds each for WebRTC setup

## Project Insights & Learnings

### WebRTC Complexity
- WebRTC is inherently complex with many moving parts
- Proper cleanup is critical to avoid resource leaks
- Connection state monitoring is essential
- ICE candidate handling can be tricky (trickle vs full)

### Async Challenges
- Mixing async and sync code requires care
- aiortc uses threads internally (unavoidable)
- Proper exception handling in async code is crucial
- Context managers help ensure cleanup

### Plugin Architecture Benefits
- Clean separation of concerns
- Easy to add new plugins
- Each plugin manages its own state
- Session provides common infrastructure

### Transport Abstraction
- WebSocket preferred for performance
- HTTP long-polling as reliable fallback
- Protocol detection from URL is convenient
- Each transport has unique challenges

### Testing Insights
- Integration tests are valuable but can be flaky
- Mock carefully to avoid false positives
- Test error paths, not just happy paths
- Async tests need special attention

## Next Steps

### Immediate (This Session)
1. ✅ Complete activeContext.md
2. ⏳ Write progress.md
3. ⏳ Verify all Memory Bank files
4. ⏳ Ensure cross-references are correct

### Short-Term (Next Release)
1. Fix WebSocket cleanup issue
2. Address deprecation warnings
3. Add more usage examples
4. Improve error messages
5. Update documentation

### Medium-Term (Next Few Months)
1. Consider optional WebRTC dependency
2. Add more plugin support (if requested)
3. Performance optimizations
4. Enhanced monitoring/debugging tools
5. More comprehensive examples

### Long-Term (Future Versions)
1. Broader Janus feature coverage
2. Advanced media processing capabilities
3. Production-grade reliability improvements
4. Enterprise features (if needed)
5. Community-requested features

## Known Issues & Workarounds

### Issue 1: WebSocket Cleanup
**Symptom:** Connections not properly closed in some scenarios  
**Workaround:** Explicitly call disconnect() if needed  
**Status:** Investigating  
**Tracking:** TODO in README.md

### Issue 2: Deprecation Warnings
**Symptom:** Warnings during documentation build  
**Workaround:** Suppress with `-W ignore::DeprecationWarning:mkdocs_autorefs`  
**Status:** Monitoring dependency updates  
**Impact:** None (warnings only)

### Issue 3: Test Flakiness
**Symptom:** Occasional test failures in WebRTC connection tests  
**Cause:** Network timing, server availability  
**Workaround:** Retry failed tests, use longer timeouts  
**Status:** Acceptable for integration tests

## Environment Notes

### Current Development Environment
- **OS:** Windows 11
- **Python:** 3.8-3.13 (testing across all)
- **IDE:** VS Code
- **Shell:** cmd.exe
- **Build Tool:** Hatch

### Test Server
- **URL:** Configured via environment variables
- **Plugins:** EchoTest, VideoCall, VideoRoom, TextRoom
- **Auth:** API key and token support

## Communication Patterns

### With Users
- Clear error messages with actionable information
- Comprehensive examples in documentation
- Responsive to issues and PRs
- Maintain backward compatibility

### With Contributors
- Clear contribution guidelines
- Code review for quality
- Test coverage requirements
- Documentation updates required

## Project Health

### Metrics
- **Test Coverage:** 82% (target: >80%) ✅
- **Python Versions:** 3.8-3.13 supported ✅
- **Dependencies:** Up to date ✅
- **Documentation:** Complete and current ✅
- **Issues:** Low count, responsive ✅

### Areas for Improvement
- WebSocket cleanup reliability
- More comprehensive examples
- Performance benchmarking
- Load testing
- Security audit

## Context for Future Sessions

### When Resuming Work
1. Read all Memory Bank files (especially this one)
2. Check recent commits for changes
3. Review open issues/PRs
4. Run tests to verify environment
5. Check TODO list in README

### Key Files to Review
- `janus_client/session.py` - Core session management
- `janus_client/plugin_textroom.py` - Latest plugin work
- `tests/test_plugin_textroom.py` - Latest tests
- `pyproject.toml` - Project configuration
- `README.md` - User-facing documentation

### Important Reminders
- Always use Hatch for development tasks
- Run tests before committing
- Build docs with strict mode
- Maintain type hints
- Keep docstrings concise but clear
- Test across Python versions
- Update Memory Bank after significant changes
