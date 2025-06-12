import os
import json
from pathlib import Path
from typing import Dict, Any

# Add python-dotenv for .env file support
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

# --------------------------------------------------
# Constants and defaults
# --------------------------------------------------

# The directory in the user's home folder to store config, DB, etc.
CONFIG_DIR = Path.home() / ".comfydock"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Settings that users can configure
CONFIGURABLE_CONFIG = {
    "comfyui_path": str(Path.home()),
    "db_file_path": str(CONFIG_DIR / "environments.json"),
    "user_settings_file_path": str(CONFIG_DIR / "user.settings.json"),
    "backend_port": 5172,
    "frontend_host_port": 8000,
    "allow_multiple_containers": False,
    "dockerhub_tags_url": "https://hub.docker.com/v2/namespaces/akatzai/repositories/comfydock-env/tags?page_size=100",
}

# Advanced user-configurable settings
ADVANCED_CONFIG = {
    "log_level": "INFO",  # Default to INFO, but allow users to change
    "check_for_updates": True,  # Whether to check for updates
    "update_check_interval_days": 1,  # Days between update checks
    "last_update_check": 0,  # Unix timestamp of last check
}

# Settings that are managed internally and not user-configurable
NON_CONFIGURABLE_CONFIG = {
    "frontend_image": "akatzai/comfydock-frontend:0.2.0",
    "frontend_container_name": "comfydock-frontend",
    "backend_host": "localhost",
    "frontend_container_port": 8000,
}

# Help text for each field (used in 'comfydock config')
CONFIG_FIELD_HELP = {
    "comfyui_path": "Default filesystem path to your local ComfyUI clone or desired location.",
    "db_file_path": "Where to store known Docker environments (JSON).",
    "user_settings_file_path": "Where to store user preferences for ComfyDock/ComfyUI.",
    "backend_port": "TCP port for the backend FastAPI server.",
    "frontend_host_port": "TCP port on your local machine for accessing the frontend.",
    "allow_multiple_containers": "Whether to allow multiple ComfyUI containers to run at once.",
    "dockerhub_tags_url": "URL to the Docker Hub API endpoint for retrieving available tags.",
    
    # Advanced settings
    "log_level": "Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL).",
    "check_for_updates": "Whether to automatically check for ComfyDock CLI updates.",
    "update_check_interval_days": "Days between update checks.",
    "last_update_check": "Unix timestamp of the last update check (internal use).",
    
    # Help text for non-configurable settings (shown in --list but not editable)
    "frontend_version": "Tag/version for the frontend container (managed automatically).",
    "frontend_image": "Docker image for the frontend container (managed automatically).",
    "frontend_container_name": "Name for the Docker container (managed automatically).",
    "backend_host": "Host/IP for the backend FastAPI server (managed automatically).",
    "frontend_container_port": "TCP port inside the container (managed automatically).",
}

# --------------------------------------------------
# Helper functions
# --------------------------------------------------

def ensure_config_dir_and_file():
    """Ensure ~/.comfydock/ exists and has a config.json."""
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_FILE.exists():
        config_data = {}
        config_data.update(CONFIGURABLE_CONFIG)
        config_data.update(ADVANCED_CONFIG)
        
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)

def load_config():
    """Load config from ~/.comfydock/config.json, creating defaults if necessary."""
    ensure_config_dir_and_file()
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg_data = json.load(f)

    # Fill in any missing configurable fields with defaults
    updated = False
    
    # Add regular configurable settings
    for key, default_value in CONFIGURABLE_CONFIG.items():
        if key not in cfg_data:
            cfg_data[key] = default_value
            updated = True
    
    # Add advanced configurable settings
    for key, default_value in ADVANCED_CONFIG.items():
        if key not in cfg_data:
            cfg_data[key] = default_value
            updated = True

    # If we updated the config with new defaults, save it back
    if updated:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg_data, f, indent=4)

    return cfg_data

def load_env_files():
    """
    Load environment variables from .env files.
    Order of precedence: .env.local > .env > actual environment
    """
    if not DOTENV_AVAILABLE:
        return False
    
    # Start with current directory
    cwd = Path.cwd()
    env_local = cwd / ".env.local"
    env_file = cwd / ".env"
    
    # Also check in CONFIG_DIR
    config_env_local = CONFIG_DIR / ".env.local"
    config_env_file = CONFIG_DIR / ".env"
    
    loaded = False
    
    # Load in order of lowest to highest precedence
    # (later loads override earlier ones)
    if env_file.exists():
        load_dotenv(env_file)
        loaded = True
        
    if config_env_file.exists():
        load_dotenv(config_env_file)
        loaded = True
        
    if env_local.exists():
        load_dotenv(env_local)
        loaded = True
        
    if config_env_local.exists():
        load_dotenv(config_env_local)
        loaded = True
        
    return loaded

def _convert_value(val):
    """
    A helper to convert user CLI input from strings to bools/ints if needed.
    Minimal example that tries bool/int, otherwise returns str.
    """
    # Try boolean
    if val.lower() in ["true", "false"]:
        return val.lower() == "true"

    # Try integer
    try:
        return int(val)
    except ValueError:
        pass

    # Fallback to string
    return val

def get_complete_config(allow_env_override: bool = True) -> Dict[str, Any]:
    """
    Get a complete config dict with both user settings and non-configurable settings.
    
    If allow_env_override is True, environment variables can override non-configurable settings
    using the format COMFYDOCK_{UPPERCASE_KEY}=value
    
    Also loads from .env and .env.local files if dotenv is available.
    """
    # Load environment variables from .env files
    if allow_env_override:
        load_env_files()
    
    cfg_data = load_config()
    
    # Add all non-configurable settings, but allow environment variable overrides if enabled
    for key, default_value in NON_CONFIGURABLE_CONFIG.items():
        # Check for environment variable override
        env_var_name = f"COMFYDOCK_{key.upper()}"
        if allow_env_override and env_var_name in os.environ:
            env_value = os.environ[env_var_name]
            cfg_data[key] = _convert_value(env_value)
        else:
            cfg_data[key] = default_value
        
    return cfg_data

def save_config(cfg_data):
    """Save config data back to ~/.comfydock/config.json."""
    # Filter out any keys that aren't in our known config dictionaries
    # This prevents non-configurable settings from being saved
    filtered_data = {}
    for k, v in cfg_data.items():
        if k in CONFIGURABLE_CONFIG or k in ADVANCED_CONFIG:
            filtered_data[k] = v
    
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(filtered_data, f, indent=4)

def get_server_config(cli_overrides: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Get only the server-specific configuration (excluding CLI-specific settings).
    This provides a filtered config suitable for passing to ServerConfig.
    
    Args:
        cli_overrides: Dictionary of CLI argument overrides to apply
    """
    # Get the complete config first
    complete_config = get_complete_config()
    
    # Create a new dict with only the keys that ServerConfig expects
    server_config = {}
    
    # Add all configurable settings except those specific to the CLI
    for key, value in complete_config.items():
        # Skip CLI-specific advanced settings
        if key in ADVANCED_CONFIG:
            continue
        server_config[key] = value
    
    # Apply CLI overrides if provided
    if cli_overrides:
        for key, value in cli_overrides.items():
            if value is not None and key in server_config:
                server_config[key] = value
    
    return server_config