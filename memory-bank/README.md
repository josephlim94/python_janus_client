# Memory Bank: Python Janus Client

This Memory Bank provides comprehensive context about the Python Janus Client project for Cline (AI assistant) to maintain continuity across sessions.

## Purpose

After each session reset, Cline relies entirely on this Memory Bank to understand the project and continue work effectively. These files serve as the single source of truth for project context, decisions, and current state.

## File Structure

### Core Files (Read in Order)

1. **[projectbrief.md](projectbrief.md)** - Foundation Document
   - Project identity and purpose
   - Core requirements and scope
   - Success criteria
   - Development principles
   - **Read this first** - shapes all other files

2. **[productContext.md](productContext.md)** - Product Understanding
   - Why this project exists
   - Problems it solves
   - How it should work
   - User experience goals
   - User personas

3. **[systemPatterns.md](systemPatterns.md)** - Architecture & Design
   - System architecture
   - Core components
   - Design patterns
   - Implementation patterns
   - Component relationships

4. **[techContext.md](techContext.md)** - Technical Setup
   - Technology stack
   - Development setup
   - Build system (Hatch)
   - Testing strategy
   - Documentation system

5. **[activeContext.md](activeContext.md)** - Current State
   - Current work focus
   - Recent changes
   - Active decisions
   - Important patterns
   - Next steps
   - **Most frequently updated**

6. **[progress.md](progress.md)** - Project Status
   - What works
   - What's left to build
   - Known issues
   - Evolution of decisions
   - Roadmap

## How to Use This Memory Bank

### Starting a New Session

1. **Always read ALL Memory Bank files** at the start of every task
2. Start with `projectbrief.md` for foundation
3. Read files in the order listed above
4. Pay special attention to `activeContext.md` for current state
5. Check `progress.md` for what's completed and what's pending

### During Work

- Reference relevant files as needed
- Keep context in mind when making decisions
- Follow established patterns and conventions
- Document significant changes

### Updating the Memory Bank

Update when:
- Discovering new project patterns
- After implementing significant changes
- When user requests "update memory bank"
- When context needs clarification

**When updating:**
1. Review ALL files (even if some don't need updates)
2. Focus on `activeContext.md` and `progress.md`
3. Update cross-references if structure changes
4. Keep information accurate and current
5. Remove outdated information

## File Relationships

```
projectbrief.md (Foundation)
    ↓
    ├─→ productContext.md (Why & How)
    ├─→ systemPatterns.md (Architecture)
    └─→ techContext.md (Technical)
         ↓
         ├─→ activeContext.md (Current State)
         └─→ progress.md (Status)
```

## Quick Reference

### Project Essentials
- **Name:** python_janus_client (PyPI: janus-client)
- **Version:** 0.8.1
- **Type:** Python async WebRTC client library
- **Build Tool:** Hatch
- **Python:** 3.8-3.13
- **Coverage:** 82%

### Key Commands
```bash
hatch env create          # Setup environment
hatch shell              # Activate environment
hatch test               # Run tests
hatch run docs-build     # Build documentation
hatch build              # Build package
```

### Key Files
- `janus_client/session.py` - Core session management
- `janus_client/plugin_*.py` - Plugin implementations
- `janus_client/transport*.py` - Transport layer
- `tests/test_*.py` - Test suite
- `pyproject.toml` - Project configuration

### Current Focus
- Memory Bank initialization (this session)
- WebSocket cleanup improvements (next priority)
- Documentation enhancements (ongoing)

### Known Issues
1. WebSocket cleanup needs improvement
2. Deprecation warnings from dependencies
3. Occasional test flakiness (acceptable)

## Important Reminders

### Development Practices
- **Always use Hatch** for development tasks
- **Run tests** before committing
- **Build docs with strict mode** to catch issues
- **Maintain type hints** throughout
- **Keep docstrings concise** but clear
- **Test across Python versions**

### Code Standards
- **Line length:** 88 characters
- **Docstrings:** Google-style
- **Type hints:** Required for public APIs
- **Async-first:** All I/O operations
- **Context managers:** For resource management

### Testing
- **Target:** >80% coverage (currently 82%)
- **Framework:** pytest with async support
- **Run:** `hatch test -i py=3.8 -c` for coverage
- **Integration tests:** May be flaky (acceptable)

## Memory Bank Maintenance

### Regular Updates
- After significant code changes
- When discovering new patterns
- When project direction changes
- When user requests update

### Quality Checks
- Ensure all cross-references are valid
- Remove outdated information
- Keep current state accurate
- Maintain consistency across files

### Version Control
- Memory Bank files are version controlled
- Track changes with meaningful commits
- Review changes during code review
- Keep in sync with code changes

## Contact & Support

For questions about the Memory Bank structure or content:
- Review this README
- Check individual file headers
- Refer to project documentation
- Ask the user for clarification

---

**Last Updated:** 2025-10-22  
**Memory Bank Version:** 1.0  
**Project Version:** 0.8.1
