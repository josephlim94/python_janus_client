# Technical Context: Python Janus Client

## Technology Stack

### Core Dependencies

#### Python Version Support
- **Supported:** Python 3.8, 3.9, 3.10, 3.11, 3.12, 3.13
- **Minimum:** Python 3.8 (for async/await features)
- **Maximum:** Python 3.13 (latest tested)
- **Reason:** Balance between modern features and broad compatibility

#### Primary Dependencies
1. **aiortc (>=1.5.0)**
   - Purpose: WebRTC implementation
   - Features: RTCPeerConnection, MediaStreamTrack, JSEP handling
   - Note: Uses PyAV internally for media processing
   - Threading: Uses threads internally for media processing

2. **websockets (>=11.0.3)**
   - Purpose: WebSocket transport implementation
   - Features: Async WebSocket client
   - Note: Modern, well-maintained library

3. **aiohttp (>=3.8.5)**
   - Purpose: HTTP transport implementation
   - Features: Async HTTP client, session management
   - Note: Used for HTTP long-polling

### Development Dependencies

#### Testing
- **pytest**: Test framework
- **pytest-asyncio**: Async test support
- **coverage**: Code coverage measurement
- **python-dotenv**: Environment variable management for tests

#### Documentation
- **mkdocs-material (>=9.6.20)**: Documentation theme
- **mkdocstrings (>=0.23.0)**: API documentation generator
- **mkdocstrings-python (>=1.7.5)**: Python-specific documentation
- **griffe (>=0.38.0)**: Python code analysis for docs

#### Code Quality
- **flake8**: Linting (configured in .flake8)
- **black**: Code formatting (88 char line length)
- **isort**: Import sorting
- **mypy**: Static type checking

## Build System: Hatch

### Why Hatch?
- Modern Python project manager
- PEP 517/518 compliant
- Unified environment management
- Integrated testing workflows
- Reproducible builds

### Project Configuration (pyproject.toml)

#### Build System
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

#### Environments
1. **default**: Main development environment
   - All dependencies installed
   - Used for general development

2. **test**: Testing environment (via hatch-test)
   - Pytest and coverage
   - Runs across all Python versions

3. **docs**: Documentation environment
   - MkDocs and plugins
   - Documentation building/serving

### Common Hatch Commands

#### Environment Management
```bash
hatch env create              # Create all environments
hatch shell                   # Activate default environment
hatch env show                # Show environment details
hatch env prune               # Remove all environments
```

#### Testing
```bash
hatch test                    # Run tests on all Python versions
hatch test -i py=3.8          # Run tests on Python 3.8 only
hatch test -- -s              # Run with output (pytest -s)
hatch test -c                 # Run with coverage
```

#### Documentation
```bash
hatch run docs-build          # Build documentation (strict mode)
hatch run docs-serve          # Serve documentation locally
```

#### Building & Publishing
```bash
hatch build                   # Build wheel and sdist
hatch publish                 # Publish to PyPI
hatch version                 # Show current version
hatch version patch           # Bump patch version
```

## Development Setup

### Initial Setup
```bash
# Clone repository
git clone https://github.com/josephlim94/janus_gst_client_py.git
cd python_janus_client

# Install Hatch (if not already installed)
pip install hatch

# Create development environment
hatch env create

# Activate environment
hatch shell

# Verify installation
python -c "import janus_client; print(janus_client.__version__)"
```

### IDE Configuration

#### VS Code
- Python extension recommended
- Configure Python interpreter to Hatch environment
- Use pytest for test discovery
- Enable type checking with mypy

#### PyCharm
- Mark `janus_client` as sources root
- Configure Python interpreter to Hatch environment
- Enable pytest as test runner
- Configure code style (88 char line length)

## Code Style & Standards

### Line Length
- **Maximum:** 88 characters (Black default)
- **Configured in:** .flake8

### Import Organization
```python
# Standard library
import asyncio
from typing import Dict, Any

# Third-party
import aiohttp
from aiortc import RTCPeerConnection

# Local
from janus_client import JanusSession
from janus_client.plugin_base import JanusPlugin
```

### Type Hints
- **Required:** All public functions and methods
- **Style:** Use typing module (Dict, List, Optional, etc.)
- **Return types:** Always specify, use None for procedures
- **Example:**
```python
async def send_message(
    self, 
    message: Dict[str, Any], 
    timeout: Optional[float] = None
) -> Dict[str, Any]:
    pass
```

### Docstrings
- **Format:** Google-style docstrings
- **Required:** All public classes, methods, functions
- **Conciseness:** Brief but clear
- **Example:**
```python
async def join_room(self, room_id: int, username: str) -> bool:
    """Join a video room.
    
    Args:
        room_id: The ID of the room to join
        username: Username to use in the room
        
    Returns:
        True if successfully joined
        
    Raises:
        JanusError: If room doesn't exist or join fails
    """
```

### Async Patterns
- **Always use:** async/await (never callbacks)
- **Context managers:** Use for resource management
- **Timeouts:** Always specify for network operations
- **Error handling:** Wrap async operations in try/except

## Testing Strategy

See .clinerules/testing-guidelines.md for comprehensive testing information.

## Documentation System

### MkDocs Configuration
- **Theme:** Material for MkDocs
- **Features:** 
  - API documentation auto-generation
  - Code syntax highlighting
  - Search functionality
  - Navigation sidebar

### Documentation Structure
```
docs/
├── index.md              # Home page
├── session.md            # Session management
├── transport.md          # Transport layer
├── plugins.md            # Plugin documentation
└── assets/              # Images and assets
```

### Building Documentation
```bash
# Build with strict mode (catches warnings as errors)
hatch run docs-build

# Serve locally for development
hatch run docs-serve

# Build without strict mode (development)
hatch run mkdocs build
```

### Documentation Standards
- **API docs:** Auto-generated from docstrings
- **Examples:** Include working code examples
- **Updates:** Keep in sync with code changes
- **Strict mode:** Always use for production builds

## Deployment

### PyPI Publishing
```bash
# Ensure version is updated in pyproject.toml
hatch version patch  # or minor, major

# Build distribution
hatch build --clean

# Publish to PyPI
hatch publish

# Publish to Test PyPI (for testing)
hatch publish -r test
```

### Version Management
- **Format:** Semantic versioning (MAJOR.MINOR.PATCH)
- **Location:** pyproject.toml [project.version]
- **Commands:**
  - `hatch version` - Show current version
  - `hatch version patch` - Bump patch (0.8.1 → 0.8.2)
  - `hatch version minor` - Bump minor (0.8.1 → 0.9.0)
  - `hatch version major` - Bump major (0.8.1 → 1.0.0)

## Technical Constraints

### Platform Support
- **Windows:** Full support (tested on Windows 11)
- **Linux:** Full support
- **macOS:** Full support
- **Note:** aiortc has platform-specific dependencies

### Performance Characteristics
- **Async I/O:** Non-blocking, efficient
- **WebRTC:** Uses threads internally (aiortc limitation)
- **Memory:** Moderate (media buffers can be large)
- **Network:** Depends on WebRTC connection quality

### Known Limitations
1. **WebSocket cleanup:** Needs improvement (see TODO in README)
2. **Deprecation warnings:** Some from dependencies
3. **WebRTC dependency:** Currently required, making it optional is planned
4. **Thread usage:** aiortc uses threads for media processing

## Environment Variables

### Development
- **PYTHONPATH:** Set to project root for imports
- **LOG_LEVEL:** Control logging verbosity

### Testing
See .clinerules/testing-guidelines.md for testing environment variables.

## CI/CD Considerations

### GitHub Actions (if configured)
- Run tests on multiple Python versions
- Check code coverage
- Build documentation
- Lint code
- Type checking

### Pre-commit Hooks (recommended)
- Run flake8
- Run black
- Run isort
- Run mypy
- Run tests

## Migration Notes

### From Poetry to Hatch
- **Completed:** Project migrated from Poetry to Hatch
- **Benefits:** Better PEP 517/518 compliance, simpler configuration
- **Breaking changes:** None for end users
- **Developer impact:** Different commands (see Hatch commands above)

### Dependency Updates
- Regular updates via Dependabot or manual review
- Test thoroughly after updates
- Document breaking changes

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Ensure environment is created
hatch env create

# Activate environment
hatch shell

# Verify installation
pip list | grep janus-client
```

#### Test Failures
```bash
# Clean and recreate environment
hatch env prune
hatch env create

# Run tests with verbose output
hatch test -- -vv
```

#### Documentation Build Errors
```bash
# Check for missing dependencies
hatch env show

# Build without strict mode to see warnings
hatch run mkdocs build

# Suppress known warnings
hatch run python -W ignore::DeprecationWarning:mkdocs_autorefs -m mkdocs build
```

#### WebRTC Connection Issues
- Check Janus server is running and accessible
- Verify firewall settings
- Check STUN/TURN server configuration
- Review aiortc logs for details

## Security Considerations

### API Keys & Tokens
- Never commit to version control
- Use environment variables
- Rotate regularly
- Use minimal permissions

### Network Security
- Always use WSS (WebSocket Secure) in production
- Always use HTTPS in production
- Validate server certificates
- Use VPN for sensitive deployments

### Dependency Security
- Regular dependency updates
- Monitor security advisories
- Use pip-audit or similar tools
- Review dependency licenses
