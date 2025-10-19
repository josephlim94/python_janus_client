# Hatch Tooling Requirements

## Primary Development Tool

**CRITICAL:** This project uses **Hatch** as its primary development and build tool. All development workflows, dependency management, testing, and build operations MUST use Hatch unless technically impossible.

## Why Hatch?

Hatch is the modern Python project manager that provides:
- Unified environment management
- Reproducible builds
- Integrated testing workflows
- Standardized project structure
- PEP 517/518 compliance

## Hatch Command Reference

### Environment Management

**Install dependencies and set up environment:**
```bash
hatch env create
```

**Activate the default environment:**
```bash
hatch shell
```

**Run commands in the environment without activation:**
```bash
hatch run <command>
```

**List all environments:**
```bash
hatch env show
```

**Remove an environment:**
```bash
hatch env remove <env-name>
```

### Dependency Management

**Add a new dependency:**
```bash
# Edit pyproject.toml [project.dependencies] section manually
# Then sync the environment
hatch env create
```

**Add a development dependency:**
```bash
# Edit pyproject.toml [tool.hatch.envs.default] section manually
# Then sync the environment
hatch env create
```

**Update dependencies:**
```bash
hatch env prune
hatch env create
```

### Testing

**Run tests:**
```bash
hatch run test
```

**Run tests with coverage:**
```bash
hatch run cov
```

**Run tests for specific Python versions:**
```bash
hatch run test:test
```

**Run a specific test file:**
```bash
hatch run pytest tests/test_plugin_textroom.py
```

**Run a specific test:**
```bash
hatch run pytest tests/test_plugin_textroom.py::TestTransportHttp::test_textroom_message_history
```

### Code Quality

**Run linting:**
```bash
hatch run lint:check
```

**Auto-fix linting issues:**
```bash
hatch run lint:fix
```

**Run type checking:**
```bash
hatch run lint:typing
```

**Format code:**
```bash
hatch run lint:fmt
```

### Documentation

**Build documentation:**
```bash
hatch run docs:build
```

**Serve documentation locally:**
```bash
hatch run docs:serve
```

**Build documentation with strict mode:**
```bash
hatch run python -W ignore::DeprecationWarning:mkdocs_autorefs -m mkdocs build --clean --strict
```

### Building and Publishing

**Build the package:**
```bash
hatch build
```

**Build wheel only:**
```bash
hatch build -t wheel
```

**Build source distribution only:**
```bash
hatch build -t sdist
```

**Publish to PyPI:**
```bash
hatch publish
```

**Publish to Test PyPI:**
```bash
hatch publish -r test
```

### Version Management

**Show current version:**
```bash
hatch version
```

**Bump version (patch):**
```bash
hatch version patch
```

**Bump version (minor):**
```bash
hatch version minor
```

**Bump version (major):**
```bash
hatch version major
```

**Set specific version:**
```bash
hatch version 1.2.3
```

## Development Workflow with Hatch

### Initial Setup
```bash
# Clone the repository
git clone <repository-url>
cd python_janus_client

# Create and activate environment
hatch env create
hatch shell

# Verify installation
hatch run python -c "import janus_client; print(janus_client.__version__)"
```

### Daily Development
```bash
# Activate environment
hatch shell

# Run tests during development
hatch run pytest tests/

# Check code quality
hatch run lint:check

# Format code
hatch run lint:fmt
```

### Before Committing
```bash
# Run full test suite
hatch run test

# Check coverage
hatch run cov

# Run linting
hatch run lint:check

# Run type checking
hatch run lint:typing

# Build documentation
hatch run docs:build
```

### Adding New Dependencies
```bash
# 1. Edit pyproject.toml to add dependency
# 2. Recreate environment
hatch env prune
hatch env create

# 3. Verify dependency is installed
hatch run python -c "import <new_package>"
```

## When NOT to Use Hatch

Hatch should be used for all development tasks. However, in rare cases where Hatch cannot be used:

1. **CI/CD Constraints:** If the CI/CD platform doesn't support Hatch, use pip with requirements files generated from pyproject.toml
2. **Legacy System Compatibility:** If deploying to systems that cannot run Hatch
3. **Docker Builds:** In minimal Docker images, pip installation from wheel may be preferred

In these cases, document the reason and provide alternative commands.

## Migration from Poetry

This project previously used Poetry. If you encounter Poetry commands in documentation or scripts:

| Poetry Command | Hatch Equivalent |
|----------------|------------------|
| `poetry install` | `hatch env create` |
| `poetry shell` | `hatch shell` |
| `poetry add <package>` | Edit pyproject.toml + `hatch env create` |
| `poetry run <command>` | `hatch run <command>` |
| `poetry build` | `hatch build` |
| `poetry publish` | `hatch publish` |
| `poetry version` | `hatch version` |
| `poetry run pytest` | `hatch run pytest` |
| `poetry run flake8` | `hatch run lint:check` |

## Environment Configuration

Hatch environments are configured in `pyproject.toml` under `[tool.hatch.envs]`. The project uses:

- **default:** Main development environment with all dependencies
- **test:** Testing environment with pytest and coverage
- **lint:** Linting environment with flake8, black, isort, mypy
- **docs:** Documentation environment with mkdocs

## Best Practices

1. **Always use Hatch commands:** Don't use pip directly in the project directory
2. **Keep pyproject.toml updated:** All dependencies must be declared in pyproject.toml
3. **Use environment-specific commands:** Use `hatch run <env>:<script>` for specific environments
4. **Regenerate environments after changes:** Run `hatch env prune && hatch env create` after modifying dependencies
5. **Document Hatch usage:** When adding new scripts or workflows, document the Hatch commands

## Troubleshooting

### Environment Issues
```bash
# Remove all environments and start fresh
hatch env prune
hatch env create
```

### Dependency Conflicts
```bash
# Check environment details
hatch env show

# Recreate specific environment
hatch env remove <env-name>
hatch env create <env-name>
```

### Command Not Found
```bash
# Ensure you're in the project directory
cd /path/to/python_janus_client

# Verify Hatch is installed
hatch --version

# If not installed, install Hatch
pip install hatch
```

## Summary

**Remember:** Use Hatch for ALL development tasks. This ensures consistency, reproducibility, and adherence to modern Python packaging standards. Only deviate from Hatch when technically impossible, and document the reason clearly.
