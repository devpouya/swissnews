# Development Setup

This document describes how to set up the development environment for the Swiss News Aggregator project.

## Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality and consistency. The hooks will automatically run before each commit to fix formatting issues and catch potential problems.

### Installation

1. Install pre-commit hooks:
```bash
make install-hooks
```

Or manually:
```bash
pip install pre-commit
pre-commit install
```

### What the hooks do

The pre-commit hooks automatically:

**Backend Python:**
- Format code with Black
- Sort imports with isort
- Check code quality with flake8
- Run type checking with mypy (optional)
- Check for security issues with bandit
- Remove trailing whitespace
- Ensure files end with newlines

**Frontend JavaScript/TypeScript:**
- Format code with Prettier
- Lint code with ESLint
- Check JSON/YAML syntax

**General:**
- Prevent committing large files
- Check for merge conflicts
- Validate YAML/JSON/TOML files

### Usage

The hooks run automatically on every commit. You can also run them manually:

```bash
# Run all hooks on all files
make run-hooks

# Run specific hook
pre-commit run black --all-files
pre-commit run prettier --all-files

# Update hook versions
make update-hooks

# Check hook configuration
make check-hooks
```

### Bypassing hooks (not recommended)

If you need to bypass hooks for some reason:
```bash
git commit --no-verify -m "your message"
```

**Note:** This is not recommended as it defeats the purpose of maintaining code quality.

### Configuration

The pre-commit configuration is in `.pre-commit-config.yaml`. The hooks are configured to:

- Use Black with 88-character line length
- Use isort with Black-compatible profile
- Use flake8 with extended ignore for Black compatibility
- Skip type checking in CI for performance
- Only run on relevant file types (Python files in backend/, JS/TS files in frontend/)

### Troubleshooting

**Hook fails with "command not found":**
- Make sure you've installed the project dependencies: `make setup`
- The hooks use their own virtual environments, so local installs aren't required

**Slow first run:**
- The first run takes longer as it installs hook environments
- Subsequent runs are much faster

**Hook keeps failing:**
- Run the hook manually to see detailed output: `pre-commit run <hook-name> --all-files`
- Some issues may need manual fixing before the hook passes

**Updating hooks:**
- Run `make update-hooks` to get the latest versions
- This updates the `.pre-commit-config.yaml` file

## Development Workflow

1. Make your changes
2. The pre-commit hooks will run automatically when you commit
3. If hooks fail, fix the issues and commit again
4. If hooks modify files (e.g., formatting), stage and commit the changes

Example:
```bash
# Make changes
git add .
git commit -m "Add new feature"
# Hooks run automatically, may modify files
git add .  # Stage any formatting changes
git commit -m "Add new feature"  # Commit again if needed
```

## Integration with CI/CD

The same quality checks that run in pre-commit hooks also run in the CI/CD pipeline. This ensures:

- Code quality is maintained
- CI builds are less likely to fail due to formatting issues
- Consistent code style across all contributors

Pre-commit hooks help catch issues early, making the development process smoother and more efficient.
