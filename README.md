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

## Usage

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
# List all current configuration values
comfydock config --list

# Update a specific config value
comfydock config comfyui_path /path/to/your/ComfyUI

# Interactive configuration mode - prompts for each setting
comfydock config
```

### Configuration Options

Here are the key configuration options you can modify:

- `comfyui_path`: Path to your local ComfyUI installation
- `backend_port`: Port for the ComfyDock backend server (default: 5172)
- `frontend_host_port`: Port for accessing the ComfyUI frontend (default: 8000)
- `frontend_version`: Version tag for the frontend container (default: 0.1.3)
- `allow_multiple_containers`: Whether to allow running multiple ComfyUI containers (default: false)

The configuration is automatically created with sensible defaults on first run.

### Workflow

A typical workflow might look like:

1. Install Docker if you haven't already
2. Install with `pip install comfydock`
3. Configure your ComfyUI path: `comfydock config comfyui_path /path/to/comfyui`
4. Start the server: `comfydock up`
5. Use ComfyUI in your browser
6. When finished, stop the server with ctrl+c or `comfydock down`