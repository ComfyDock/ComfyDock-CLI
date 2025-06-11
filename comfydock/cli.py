import os
import sys
import json
import click
import signal
import logging
import webbrowser
import time
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

# For package version detection
try:
    from importlib.metadata import version as get_version
    PACKAGE_VERSION = get_version("comfydock")
except (ImportError, ModuleNotFoundError):
    # Either importlib.metadata is not available (Python < 3.8)
    # or the package is not installed (development mode)
    try:
        # Fallback to pkg_resources for Python < 3.8
        from pkg_resources import get_distribution
        PACKAGE_VERSION = get_distribution("comfydock").version
    except (ImportError, ModuleNotFoundError):
        # If all else fails, use frontend version as a fallback
        PACKAGE_VERSION = "0.1.0"  # Default development version

# Add python-dotenv for .env file support
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

# For version checking
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Import from your ComfyDock server package:
# Make sure to install comfydock_server==0.1.4 so these imports work:
from comfydock_server.server import ComfyDockServer
from comfydock_server.config import ServerConfig

# --------------------------------------------------
# Constants and defaults
# --------------------------------------------------

# The directory in the user's home folder to store config, DB, etc.
CONFIG_DIR = Path.home() / ".comfydock"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Valid logging levels
VALID_LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

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

def configure_logging():
    """
    Configure logging to write to a rotating log file.
    Uses the configured log level from settings.
    """
    ensure_config_dir_and_file()
    
    # Get the config to read log_level
    cfg_data = load_config()
    log_level_str = cfg_data.get("log_level", "INFO").upper()
    
    # Validate log level and convert to int
    if log_level_str not in VALID_LOG_LEVELS:
        log_level_str = "INFO"  # Default if invalid
    
    log_level = VALID_LOG_LEVELS[log_level_str]
    
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Remove any existing handlers so we don't print to console
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    log_file_path = CONFIG_DIR / "comfydock.log"

    # Set up rotating file handler
    file_handler = RotatingFileHandler(
        filename=str(log_file_path),
        maxBytes=20 * 1024 * 1024,  # ~20MB
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    
    # Set up formatter for human-readable messages
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Add the handler to the logger
    logger.addHandler(file_handler)
    
    logger.info(f"Logging initialized with level {log_level_str}")
    
    return logger

def check_for_updates(logger) -> Tuple[bool, str]:
    """
    Check if a newer version of comfydock_cli is available on PyPI.
    
    Returns:
        Tuple of (update_available, latest_version)
    """
    if not REQUESTS_AVAILABLE:
        logger.warning("Cannot check for updates: requests package not installed")
        return False, ""
    
    try:
        # Load config to get update settings
        cfg_data = load_config()
        if not cfg_data.get("check_for_updates", True):
            logger.debug("Update checking is disabled in config")
            return False, ""
        
        # Check if we've checked recently
        last_check = cfg_data.get("last_update_check", 0)
        interval_days = cfg_data.get("update_check_interval_days", 1)
        now = int(time.time())
        
        # If we checked less than interval_days ago, skip the check
        if last_check > 0:
            next_check_time = last_check + (interval_days * 86400)  # 86400 seconds in a day
            if now < next_check_time:
                logger.debug(f"Skipping update check (last check: {last_check}, next: {next_check_time})")
                return False, ""
        
        # Update the last check timestamp
        cfg_data["last_update_check"] = now
        save_config(cfg_data)
        
        # Query PyPI for the latest version
        logger.debug("Checking for new version on PyPI")
        response = requests.get(
            "https://pypi.org/pypi/comfydock/json",
            timeout=5,  # 5 second timeout
        )
        
        if response.status_code != 200:
            logger.warning(f"Failed to check for updates: HTTP {response.status_code}")
            return False, ""
        
        data = response.json()
        latest_version = data["info"]["version"]
        
        # Parse and compare versions
        from packaging import version as pkg_version
        current = pkg_version.parse(PACKAGE_VERSION)
        latest = pkg_version.parse(latest_version)
        
        if latest > current:
            logger.info(f"New version available: {latest_version} (current: {PACKAGE_VERSION})")
            return True, latest_version
        
        logger.debug(f"Current version {PACKAGE_VERSION} is up to date")
        return False, ""
        
    except Exception as e:
        logger.warning(f"Error checking for updates: {str(e)}")
        return False, ""

def get_server_config() -> Dict[str, Any]:
    """
    Get only the server-specific configuration (excluding CLI-specific settings).
    This provides a filtered config suitable for passing to ServerConfig.
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
    
    return server_config

# --------------------------------------------------
# CLI Commands
# --------------------------------------------------

@click.group()
@click.version_option(PACKAGE_VERSION, prog_name="ComfyDock CLI")
def cli():
    """ComfyDock CLI - Manage ComfyUI Docker environments.
    
    A tool for running and managing ComfyUI installations with Docker.
    """
    pass


@cli.command()
@click.option("--backend", is_flag=True, help="Start only the backend server without the frontend")
def up(backend):
    """
    Start the ComfyDock server and the Docker-based frontend.

    This command loads configuration from ~/.comfydock/config.json (creating
    defaults if needed) and starts up both the FastAPI backend and the
    Docker frontend container.
    
    With --backend flag, only starts the backend server without the frontend.
    """
    logger = configure_logging()
    logger.info("Running 'comfydock up'...")
    
    # Check for updates at startup
    update_available, latest_version = check_for_updates(logger)

    # Get server config, excluding CLI-specific settings
    server_config_dict = get_server_config()
    server_config = ServerConfig(**server_config_dict)

    # Create and start the server
    server = ComfyDockServer(server_config)
    
    if backend:
        logger.info("Starting ComfyDockServer (backend only)...")
        click.echo("Starting ComfyDockServer (backend only)...")
        server.start_backend()
        status_message = "ComfyDock backend is now running!"
    else:
        logger.info("Starting ComfyDockServer (backend + frontend)...")
        click.echo("Starting ComfyDockServer (backend + frontend)...")
        server.start()
        status_message = "ComfyDock is now running!"
        
        # Wait for frontend to be ready before opening browser
        frontend_url = f"http://localhost:{server_config.frontend_host_port}"
        if wait_for_frontend_ready(frontend_url, logger):
            try:
                logger.info(f"Frontend is ready, opening browser to {frontend_url}")
                webbrowser.open_new_tab(frontend_url)
            except Exception as e:
                logger.warning(f"Could not open browser: {e}")
        else:
            logger.warning("Frontend did not become ready in the expected time")

    # If an update is available, show notification
    if update_available:
        click.secho("\n" + "=" * 60, fg="yellow", bold=True)
        click.secho(f" 🔄 Update Available! ComfyDock CLI v{latest_version} ", fg="yellow", bold=True)
        click.echo(f" Your version: v{PACKAGE_VERSION}")
        click.echo("")
        click.echo(" To update, run:")
        click.secho("   pip install --upgrade comfydock", fg="green")
        click.secho("=" * 60 + "\n", fg="yellow", bold=True)

    # Print a nicely formatted message for the user
    click.secho("\n" + "=" * 60, fg="cyan", bold=True)
    click.secho(f"  {status_message}", fg="green", bold=True)
    
    # Always show backend URL
    click.secho(f"  Backend API:        http://{server_config.backend_host}:{server_config.backend_port}", fg="cyan")
    
    if not backend:
        click.secho(f"  Frontend UI:        http://localhost:{server_config.frontend_host_port}", fg="cyan")
    
    click.secho("  Press Ctrl+C here to stop the server at any time.", fg="yellow")
    click.secho("=" * 60 + "\n", fg="cyan", bold=True)

    # Cross-platform wait for keyboard interrupt instead of signal.pause()
    try:
        # Simple cross-platform event loop that works on Windows and Unix
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Keyboard interrupt or system exit caught. Stopping the server.")
        # Clear the previous console output message with a shutdown message
        click.secho("\n" + "=" * 60, fg="cyan", bold=True)
        click.secho("  ComfyDock is shutting down...", fg="yellow", bold=True)
        click.secho("=" * 60 + "\n", fg="cyan", bold=True)
        server.stop()
        click.echo("Server has been stopped.")


@cli.command()
def down():
    """
    Stop the running ComfyDock server (backend + frontend).
    
    If you started the server in another terminal, calling 'down' here attempts
    to stop the same environment.
    """
    logger = configure_logging()
    logger.info("Running 'comfydock down'...")

    # Get complete config including non-configurable settings
    cfg_data = get_complete_config()
    server_config = ServerConfig(**cfg_data)
    server = ComfyDockServer(server_config)

    logger.info("Stopping ComfyDockServer (backend + frontend)...")
    server.stop()
    click.echo("Server has been stopped.")


@cli.command()
@click.option("--list", "list_config", is_flag=True,
              help="List the current configuration values.")
@click.option("--all", "show_all", is_flag=True,
              help="Include advanced and non-configurable settings.")
@click.option("--advanced", is_flag=True,
              help="Show or modify advanced configuration options.")
@click.argument("field", required=False)
@click.argument("value", required=False)
def config(list_config, show_all, advanced, field, value):
    """Manage or display ComfyDock config values.
    
    USAGE MODES:
    
      • Interactive mode: Run without arguments to edit each field\n
      • List mode: Use --list to display current settings\n
      • Direct mode: Specify FIELD VALUE to set a specific setting\n
    
    EXAMPLES:
    
      comfydock config comfyui_path /home/user/ComfyUI\n
      comfydock config --advanced log_level DEBUG
    
    CONFIGURABLE FIELDS:
    
      comfyui_path, db_file_path, user_settings_file_path,
      backend_port, frontend_host_port, allow_multiple_containers,
      dockerhub_tags_url
    
    ADVANCED FIELDS (requires --advanced or --all):
    
      log_level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logger = configure_logging()
    logger.info("Running 'comfydock config'...")

    cfg_data = load_config()

    if list_config:
        click.echo("Current ComfyDock config:\n")
        
        # Display configurable settings
        click.secho("User-Configurable Settings:", fg="green", bold=True)
        for k, v in cfg_data.items():
            if k in CONFIGURABLE_CONFIG:
                desc = CONFIG_FIELD_HELP.get(k, "")
                click.echo(f"  {k} = {v}")
                if desc:
                    click.echo(f"     -> {desc}")
        
        # Display advanced settings if requested
        if advanced or show_all:
            click.echo("\n")
            click.secho("Advanced Settings:", fg="blue", bold=True)
            for k, v in cfg_data.items():
                if k in ADVANCED_CONFIG:
                    desc = CONFIG_FIELD_HELP.get(k, "")
                    click.echo(f"  {k} = {v}")
                    if desc:
                        click.echo(f"     -> {desc}")
        
        # Display non-configurable settings if requested
        if show_all:
            click.echo("\n")
            click.secho("Non-Configurable Settings (Managed Automatically):", fg="yellow", bold=True)
            complete_cfg = get_complete_config()
            for k, v in complete_cfg.items():
                if k in NON_CONFIGURABLE_CONFIG:
                    desc = CONFIG_FIELD_HELP.get(k, "")
                    click.echo(f"  {k} = {v}")
                    if desc:
                        click.echo(f"     -> {desc}")
        return

    # If a user specified a field and value: set it directly
    if field and value:
        is_advanced = field in ADVANCED_CONFIG
        is_regular = field in CONFIGURABLE_CONFIG
        
        if not (is_advanced or is_regular):
            if field in NON_CONFIGURABLE_CONFIG:
                click.echo(f"Error: '{field}' is managed automatically and cannot be changed.")
            else:
                click.echo(f"Error: '{field}' is not a recognized config field.")
            return
        
        # Handle special validation for log_level
        if field == "log_level":
            value = value.upper()
            if value not in VALID_LOG_LEVELS:
                click.echo(f"Error: '{value}' is not a valid log level.")
                click.echo(f"Valid levels are: {', '.join(VALID_LOG_LEVELS.keys())}")
                return
        
        # Set the value
        cfg_data[field] = _convert_value(value)
        save_config(cfg_data)
        click.echo(f"Set '{field}' to '{value}' in {CONFIG_FILE}")
        return

    # Otherwise, do a short interactive update on fields
    config_keys = list(CONFIGURABLE_CONFIG.keys())
    if advanced or show_all:
        config_keys.extend(ADVANCED_CONFIG.keys())
    
    click.echo("Configure ComfyDock settings (press Enter to keep current values):")
    for k in config_keys:
        current_val = cfg_data.get(k, "")
        desc = CONFIG_FIELD_HELP.get(k, "")
        
        # Add special handling for log_level
        if k == "log_level":
            valid_options = ", ".join(VALID_LOG_LEVELS.keys())
            click.echo(f"\nLogging level ({valid_options}):")
        elif desc:
            click.echo(f"\n{desc}")
            
        new_val = click.prompt(f"{k}", default=str(current_val))
        
        # Validate log_level if that's what's being set
        if k == "log_level":
            new_val = new_val.upper()
            if new_val not in VALID_LOG_LEVELS:
                click.echo(f"Warning: '{new_val}' is not a valid log level, using default 'INFO'")
                new_val = "INFO"
                
        cfg_data[k] = _convert_value(new_val)

    save_config(cfg_data)
    click.echo("\nConfiguration updated successfully!")

@cli.group()
def dev():
    """
    Development tools for ComfyDock developers.
    
    These commands provide information about the current configuration
    and help generate template .env files for development.
    """
    pass

@dev.command()
def status():
    """Show current configuration with any developer overrides applied."""
    # Load .env files for the check
    env_loaded = load_env_files()
    
    # Get config with overrides
    cfg_with_overrides = get_complete_config(allow_env_override=True)
    
    # Get default config without overrides for comparison
    cfg_default = {}
    cfg_default.update(load_config())
    for k, v in NON_CONFIGURABLE_CONFIG.items():
        cfg_default[k] = v
    
    click.secho("ComfyDock Configuration Status:", fg="magenta", bold=True)
    
    if DOTENV_AVAILABLE:
        click.echo("\nEnvironment files:")
        if env_loaded:
            click.echo("  .env files were loaded")
        else:
            click.echo("  No .env files found")
    else:
        click.echo("\nNote: Install python-dotenv to use .env files")
        click.echo("  pip install python-dotenv")
    
    click.echo("\nUser-Configurable Settings:")
    for k in CONFIGURABLE_CONFIG:
        click.echo(f"  {k} = {cfg_with_overrides.get(k, 'N/A')}")
    
    click.echo("\nNon-Configurable Settings:")
    for k in NON_CONFIGURABLE_CONFIG:
        val = cfg_with_overrides.get(k, 'N/A')
        default_val = cfg_default.get(k, 'N/A')
        
        if val != default_val:
            # This value has been overridden
            click.secho(f"  {k} = {val}", fg="yellow")
            click.echo(f"    (default: {default_val})")
        else:
            click.echo(f"  {k} = {val}")
    
    click.echo("\nDeveloper Environment Variables:")
    for k in NON_CONFIGURABLE_CONFIG:
        env_var_name = f"COMFYDOCK_{k.upper()}"
        if env_var_name in os.environ:
            click.secho(f"  {env_var_name}={os.environ[env_var_name]}", fg="yellow")

@dev.command()
def env_setup():
    """Generate template .env files for development overrides."""
    if not DOTENV_AVAILABLE:
        click.secho("Error: python-dotenv package is not installed.", fg="red", bold=True)
        click.echo("Install it with: pip install python-dotenv")
        return
    
    # Create .env template with all non-configurable settings
    env_file = Path.cwd() / ".env"
    if not env_file.exists() or click.confirm(f"{env_file} already exists. Overwrite?"):
        with open(env_file, "w") as f:
            f.write("# ComfyDock Development Environment\n")
            f.write("# This file can be checked into git with default values.\n\n")
            
            for key, value in NON_CONFIGURABLE_CONFIG.items():
                f.write(f"# COMFYDOCK_{key.upper()}={value}\n")
        
        click.secho(f"Created {env_file}", fg="green")
        click.echo("Uncomment any variables you want to override.")
    
    # Create .env.local template
    env_local_file = Path.cwd() / ".env.local"
    if not env_local_file.exists() or click.confirm(f"{env_local_file} already exists. Overwrite?"):
        with open(env_local_file, "w") as f:
            f.write("# ComfyDock Local Development Environment\n")
            f.write("# This file should NOT be checked into git.\n\n")
            
            for key, value in NON_CONFIGURABLE_CONFIG.items():
                f.write(f"# COMFYDOCK_{key.upper()}={value}\n")
        
        click.secho(f"Created {env_local_file}", fg="green")
        click.echo("Uncomment and modify any variables you want to override.")
        click.echo("These values will take precedence over .env file values.")
    
    # Add .env.local to .gitignore if it exists
    gitignore_file = Path.cwd() / ".gitignore"
    if gitignore_file.exists():
        with open(gitignore_file, "r") as f:
            content = f.read()
        
        if ".env.local" not in content:
            with open(gitignore_file, "a") as f:
                f.write("\n# Local development environment\n.env.local\n")
            click.echo("Added .env.local to .gitignore")

@cli.command()
def update():
    """
    Check for updates to ComfyDock CLI.
    
    This command checks PyPI for newer versions of comfydock-cli
    and provides instructions for updating if available.
    """
    logger = configure_logging()
    logger.info("Running 'comfydock update'...")
    
    if not REQUESTS_AVAILABLE:
        click.secho("Error: The 'requests' package is required for update checking.", fg="red")
        click.echo("Install it with: pip install requests")
        return
    
    click.echo("Checking for updates to ComfyDock CLI...")
    
    # Force check for updates regardless of last check time
    cfg_data = load_config()
    cfg_data["last_update_check"] = 0
    save_config(cfg_data)
    
    update_available, latest_version = check_for_updates(logger)
    
    if update_available:
        click.secho(f"\n✨ A new version of ComfyDock CLI is available! ✨", fg="green", bold=True)
        click.echo(f"Current version: {PACKAGE_VERSION}")
        click.echo(f"Latest version:  {latest_version}")
        click.echo("\nTo update, run:")
        click.secho("  pip install --upgrade comfydock", fg="cyan")
    else:
        click.secho(f"\n✓ You're using the latest version of ComfyDock CLI (v{PACKAGE_VERSION}).", fg="green")

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

def wait_for_frontend_ready(url: str, logger, timeout: int = 30, check_interval: float = 1.0) -> bool:
    """
    Wait for the frontend to be ready by polling the URL.
    
    Args:
        url: The URL to check
        logger: Logger instance
        timeout: Maximum time to wait in seconds
        check_interval: Time between checks in seconds
        
    Returns:
        bool: True if frontend is ready, False if timed out
    """
    logger.info(f"Waiting for frontend at {url} to be ready (timeout: {timeout}s)")
    
    if not REQUESTS_AVAILABLE:
        logger.warning("Requests package not available, cannot check if frontend is ready")
        # If we can't check, wait a reasonable time then assume it's ready
        time.sleep(5)
        return True
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Try to connect to the frontend
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                logger.info(f"Frontend is ready after {time.time() - start_time:.1f} seconds")
                return True
        except requests.RequestException:
            # Expected during startup, not an error
            pass
        
        # Wait a bit before trying again
        time.sleep(check_interval)
    
    logger.warning(f"Timeout ({timeout}s) waiting for frontend to be ready")
    return False

def main(argv=None):
    """The main entry point for the CLI."""
    if argv is None:
        # No arguments passed in, default to sys.argv[1:]
        argv = sys.argv[1:]
    elif isinstance(argv, str):
        # If someone called main("up"), split it into ["up"]
        argv = argv.split()

    # Invoke Click, passing in our arguments list
    cli.main(args=argv, prog_name="comfydock")

if __name__ == "__main__":
    main()
