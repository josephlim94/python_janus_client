# GitHub Actions Workflows

## Documentation Deployment

The `docs.yml` workflow automatically builds and deploys the project documentation to GitHub Pages.

### Workflow Details

- **Trigger**: Runs on pushes to `master` branch, pull requests to master, and manual dispatch
- **Build**: Uses Poetry to install dependencies and MkDocs to build the documentation
- **Deploy**: Automatically deploys to GitHub Pages on pushes to master branch

### Setup Requirements

1. **GitHub Pages**: Enable GitHub Pages in your repository settings
   - Go to Settings → Pages
   - Set Source to "GitHub Actions"

2. **Dependencies**: The workflow uses:
   - Python 3.11
   - Poetry for dependency management
   - MkDocs Material theme
   - GitHub Actions for deployment

### Workflow Steps

1. **Build Job**:
   - Checkout repository
   - Set up Python and Poetry
   - Cache dependencies for faster builds
   - Install development dependencies
   - Build documentation with MkDocs
   - Upload build artifacts

2. **Deploy Job** (only on master):
   - Deploy artifacts to GitHub Pages
   - Set up custom domain if configured

### Local Testing

To test the documentation build locally:

```bash
# Install dependencies
poetry install --only=dev

# Build documentation
poetry run mkdocs build --clean --strict

# Serve locally for development
poetry run mkdocs serve
```

### Configuration

The documentation is configured in:
- `mkdocs.yml` - MkDocs configuration
- `docs/` - Documentation source files
- `site/` - Generated documentation (auto-generated, don't commit)

### Site URL

The documentation will be available at:
`https://josephlim94.github.io/python_janus_client/`

### Branch Configuration

This workflow is configured to work with the `master` branch only:
- Builds on pushes to master
- Builds on pull requests targeting master
- Deploys only from master branch
