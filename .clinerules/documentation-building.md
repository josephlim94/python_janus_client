# Documentation Building Guidelines

## Building Documentation with Strict Mode

The project uses MkDocs with Material theme for documentation. All documentation builds **MUST** use strict mode to catch warnings as errors and ensure documentation quality.

### Correct Build Command

The documentation build command is defined in `pyproject.toml` and includes:
- `--strict` flag to treat warnings as errors
- Suppression of known deprecation warnings from mkdocs-autorefs

**Always use:**
```bash
hatch run docs-build
```

This executes:
```bash
python -W ignore::DeprecationWarning:mkdocs_autorefs -m mkdocs build --clean --strict
```

### Why Strict Mode?

Strict mode ensures:
- All documentation links are valid
- All API references resolve correctly
- Type annotations are complete
- No broken cross-references
- Documentation quality is maintained

### Common Issues and Solutions

#### Issue: Missing Type Annotations for **kwargs

**Error:**
```
WARNING - griffe: janus_client\plugin_name.py:123: No type or annotation for parameter '**kwargs'
```

**Solution:**
Add `Any` type annotation to `**kwargs`:
```python
from typing import Any

def __init__(self, **kwargs: Any) -> None:
    """Initialize the plugin."""
    super().__init__(**kwargs)
```

#### Issue: Broken API References

**Error:**
```
ERROR - mkdocstrings: janus_client.SomeClass could not be found
```

**Solution:**
- Verify the class/function exists in the codebase
- Check the import path is correct
- Ensure the class is exported in `__init__.py` if needed
- Remove references to non-existent classes from `docs/reference.md`

#### Issue: Deprecation Warnings

**Error:**
```
DeprecationWarning: ... from mkdocs_autorefs
```

**Solution:**
These are suppressed in the build command. If new deprecation warnings appear:
1. Check if they're from mkdocs-autorefs (can be suppressed)
2. If from our code, fix the deprecated usage
3. Update the build command in `pyproject.toml` if needed

### Local Development

For local development without strict mode (faster iteration):
```bash
hatch run mkdocs serve
```

Or build without strict mode:
```bash
hatch run mkdocs build
```

**Note:** Always verify with strict mode before committing!

### Serving Documentation Locally

To preview documentation with live reload:
```bash
hatch run docs-serve
```

This will start a local server at http://127.0.0.1:8000/

### Documentation Structure

```
docs/
├── index.md           # Home page with getting started
├── plugins.md         # Plugin usage examples
├── reference.md       # Auto-generated API reference
├── session.md         # Session management guide
├── transport.md       # Transport layer guide
└── assets/           # Images and static files
```

### Best Practices

1. **Always build with strict mode before committing**
   ```bash
   hatch run docs-build
   ```

2. **Test documentation locally**
   ```bash
   hatch run docs-serve
   ```

3. **Keep type annotations complete**
   - All public functions must have type hints
   - Use `Any` for `**kwargs` parameters
   - Use `Optional` for optional parameters

4. **Verify API references**
   - Check that all classes/functions referenced in `docs/reference.md` exist
   - Remove references to deleted or renamed classes
   - Update references when refactoring

5. **Follow documentation philosophy**
   - Keep it simple and concise
   - Focus on common use cases
   - Don't clutter with advanced configuration details
   - See `.clinerules/documentation-philosophy.md`

### CI/CD Integration

The documentation build should be part of CI/CD pipeline:
```yaml
- name: Build documentation
  run: hatch run docs-build
```

This ensures documentation quality is maintained across all contributions.

### Troubleshooting

If documentation build fails:

1. **Read the error message carefully** - it usually points to the exact issue
2. **Check the file and line number** mentioned in the error
3. **Verify type annotations** are complete
4. **Check API references** in `docs/reference.md`
5. **Test locally** with `hatch run docs-serve` to see the issue in context

### Summary

- ✅ Always use `hatch run docs-build` for production builds
- ✅ Strict mode is mandatory for quality assurance
- ✅ Complete type annotations for all `**kwargs`
- ✅ Verify all API references resolve correctly
- ✅ Test locally before committing
- ✅ Follow the documentation philosophy
