# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ComfyDock CLI is a Python command-line tool that manages ComfyUI environments using Docker. It acts as a wrapper around the `comfydock-server` FastAPI backend and provides an easy interface for users to run ComfyUI in containerized environments.

## Development Commands

### Environment Setup
```bash
# Ensure using the correct venv with this environment variable:
VIRTUAL_ENV=~/projects/comfydock/comfydock-cli/.venv

# Install dependencies (uses modern uv package manager)
uv sync

# Install in development mode
uv pip install -e .
```

### Building and Testing
```bash
# Build the package
uv build

# Test CLI during development
uv run python -m comfydock.cli --help
uv run python -m comfydock.cli dev status

# Test specific commands
uv run python -m comfydock.cli up --help
uv run python -m comfydock.cli config --list
```

### Development Tools
```bash
# Generate .env template files for development overrides
uv run python -m comfydock.cli dev env-setup

# View current config with active overrides highlighted
uv run python -m comfydock.cli dev status
```

## Architecture

The project follows a modular CLI architecture:

- **`cli.py`**: Main entry point using Click framework, routes commands
- **`commands/`**: Individual command implementations (`server.py`, `config.py`, `dev.py`, `update.py`)
- **`core/`**: Business logic (`config.py`, `logging.py`, `updates.py`)
- **`utils/`**: Shared helper functions

### Key Dependencies
- **Click**: CLI framework for command structure
- **comfydock-server**: FastAPI backend that does the heavy lifting
- **python-dotenv**: Environment variable management
- **Docker**: External dependency for container management

## Configuration System

The app uses a hierarchical configuration system:
1. Default config (`comfydock/config.json`)
2. User config (`~/.comfydock/config.json`)
3. Environment variables (prefix: `COMFYDOCK_`)
4. .env files (`.env`, `.env.local` - gitignored)

Configuration is managed through `core/config.py` with interactive CLI editing via `commands/config.py`.

## Development Environment Variables

All internal settings can be overridden with `COMFYDOCK_` prefixed environment variables:
- `COMFYDOCK_FRONTEND_IMAGE`: Override Docker image
- `COMFYDOCK_BACKEND_PORT`: Change backend port
- `COMFYDOCK_LOG_LEVEL`: Set logging verbosity

Use `comfydock dev env-setup` to generate template .env files.

## Important File Locations

- **User data**: `~/.comfydock/` (config.json, environments.json, user.settings.json, logs)
- **Package data**: `comfydock/config.json` (default configuration template)
- **Development overrides**: `.env.local` (gitignored, created by dev tools)

## Code Patterns

- Uses Click's command groups and decorators extensively
- Configuration loading follows a specific order (defaults → user → env vars → .env files)
- All file I/O goes through `core/config.py` helper functions
- Logging is centralized in `core/logging.py`
- Commands should use the shared config system rather than direct file access

## Testing and Quality

The project currently lacks formal testing infrastructure (no pytest, linting, or type checking configured). When adding these tools, follow modern Python practices and integrate with the existing uv-based workflow.