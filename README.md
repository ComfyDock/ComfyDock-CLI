# ComfyDock CLI

ComfyDock CLI is a CLI tool for managing ComfyUI environments using ComfyDock and Docker. It is currently a wrapper around the ComfyDock server.

## Prerequisites

- **Docker**: ComfyDock requires Docker to be installed on your system
  - If you don't have Docker installed, you can download [Docker Desktop](https://www.docker.com/products/docker-desktop/) for Windows, macOS, or Linux
  - For server environments, you can install [Docker Engine](https://docs.docker.com/engine/install/)

## Installation

```bash
pip install comfydock
```

## Quickstart

```bash
# Start ComfyDock (backend + frontend)
comfydock up

# Stop ComfyDock
comfydock down

# Configure settings
comfydock config

# Check for updates
comfydock update
```

## Commands

ComfyDock CLI provides several commands to manage your ComfyUI Docker environments:

### Getting Help

```bash
comfydock --help       # Show main help
comfydock up --help    # Show help for a specific command
```

### Starting and Stopping the Server

```bash
# Start both backend and frontend (opens in browser automatically)
comfydock up

# Start only the backend server without the frontend
comfydock up --backend

# Stop the running server (both backend and frontend)
comfydock down
```

### Managing Configuration

ComfyDock stores its configuration in `~/.comfydock/config.json`. You can view and modify this configuration with:

```bash
# Interactive configuration
comfydock config

# View current configuration
comfydock config --list

# View all settings (including advanced and internal)
comfydock config --list --all

# Show/edit advanced settings
comfydock config --advanced

# Directly set a value
comfydock config comfyui_path /home/user/comfy_ui
comfydock config --advanced log_level DEBUG
```

### Available Settings

#### Basic settings:
- `comfyui_path`: Path to your ComfyUI installation
- `db_file_path`: Where to store environment data
- `user_settings_file_path`: Where to store user preferences
- `backend_port`: Port for the FastAPI backend server
- `frontend_host_port`: Port for accessing the frontend UI
- `allow_multiple_containers`: Whether to allow multiple containers
- `dockerhub_tags_url`: URL for retrieving Docker image tags

#### Advanced settings:
- `log_level`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `check_for_updates`: Whether to automatically check for updates
- `update_check_interval_days`: Days between update checks

### Updates

```bash
# Check for updates
comfydock update
```

To update ComfyDock CLI to the latest version:

```bash
pip install --upgrade comfydock
```

### Workflow

A typical workflow might look like:

1. Install Docker if you haven't already
2. Install with `pip install comfydock`
3. Configure your ComfyUI path: `comfydock config comfyui_path /path/to/comfyui`
4. Start the server: `comfydock up`
5. Use ComfyUI in your browser
6. When finished, stop the server with ctrl+c or `comfydock down`

### Developer Features

ComfyDock includes developer tools for those contributing to the project or needing to override internal settings.

#### Environment Variables

You can override internal settings using environment variables with the COMFYDOCK_ prefix:

```bash
# Override the frontend image
export COMFYDOCK_FRONTEND_IMAGE=mycustom/comfydock-frontend
comfydock up
```

### .env File Support
For convenience, ComfyDock supports .env and .env.local files for persistent overrides:

```bash
# Create template .env files
comfydock dev env-setup

# Edit the files and uncomment values you want to override
nano .env.local
```

.env.local takes precedence and is gitignored by default. It's perfect for personal development settings.

#### View Configuration Status

```bash
comfydock dev status
```

This shows your current configuration with any active overrides highlighted.

### Logging

Logs are stored in ~/.comfydock/comfydock.log with a configurable log level. You can change the log level:

```bash
comfydock config --advanced log_level DEBUG
```

### Configuration File Location

All settings are stored in:
- ~/.comfydock/config.json - User configuration
- ~/.comfydock/environments.json - Environment database
- ~/.comfydock/user.settings.json - User preferences


#### Contributing

ComfyDock is an open source project. Contributions are welcome on [GitHub](https://github.com/ComfyDock/ComfyDock-CLI).

To set up a development environment:

1. Clone the repository
2. Install with pip in development mode: `pip install -e .`
3. Create dev override files: `comfydock dev env-setup`
4. Run with your changes: `comfydock up`



