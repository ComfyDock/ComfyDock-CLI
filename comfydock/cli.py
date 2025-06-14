import sys
import click
from pathlib import Path

from .core.updates import get_package_version
from .core.logging import configure_logging, get_safe_logger
from .core.config import (
    UserEditableConfig, load_config as cli_load_config, DEFAULT_CONFIG_FILE, 
    map_user_config_to_app_config, load_env_files, load_env_overrides, merge_user_configs
)
from .utils.helpers import ensure_config_directories
from .commands.server import up, down
from .commands.config import config
from .commands.dev import dev
from .commands.update import update

@click.group()
@click.version_option(get_package_version(), prog_name="ComfyDock CLI")
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']), 
              help='Set the logging level (overrides config file)')
@click.option('--quiet', '-q', is_flag=True, help='Suppress all output except errors')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output (DEBUG level)')
@click.option("--config-file", type=str, help="Path to config file")
@click.option("--comfyui-path", type=str, help="Path to ComfyUI installation")
@click.option("--db-file-path", type=str, help="Path to environments database file")
@click.option("--user-settings-file-path", type=str, help="Path to user settings file")
@click.option("--log-file-path", type=str, help="Path to the log file")
@click.option("--backend-port", type=int, help="Backend server port")
@click.option("--frontend-host-port", type=int, help="Frontend host port")
@click.option("--allow-multiple-containers", type=bool, help="Allow running multiple containers")
@click.pass_context
def cli(ctx, log_level, quiet, verbose, config_file, comfyui_path, db_file_path, user_settings_file_path, log_file_path, backend_port, frontend_host_port, allow_multiple_containers):
    """ComfyDock CLI - Manage ComfyUI Docker environments.
    
    A tool for running and managing ComfyUI installations with Docker.
    """
    # Load and configure the application config first
    try:
        # Import here to avoid circular imports
        from comfydock_server.config import AppConfig, load_config
        
        # Load .env files first (this loads them into os.environ)
        load_env_files()
        
        # Get default config with client defaults
        client_defaults_path = Path(__file__).parent / "cli_defaults.json"
        app_config: AppConfig = load_config(client_defaults_path=client_defaults_path)
        
        # Load user config from file
        user_config_path = DEFAULT_CONFIG_FILE if config_file is None else config_file
        user_config: UserEditableConfig = cli_load_config(config_file_path=user_config_path, logger=None)
        
        # Load environment variable overrides
        env_overrides: UserEditableConfig = load_env_overrides()
        
        # Merge user config with environment overrides (env vars take precedence)
        user_config = merge_user_configs(user_config, env_overrides)
        
        # Map user config to app config structure
        app_config = map_user_config_to_app_config(user_config, app_config)
        
        # Apply CLI overrides if provided (highest precedence)
        if backend_port is not None:
            app_config.backend.port = backend_port
        if frontend_host_port is not None:
            app_config.frontend.default_host_port = frontend_host_port
        if comfyui_path is not None:
            app_config.defaults.comfyui_path = comfyui_path
        if db_file_path is not None:
            app_config.defaults.db_file_path = db_file_path
        if user_settings_file_path is not None:
            app_config.defaults.user_settings_file_path = user_settings_file_path
        if allow_multiple_containers is not None:
            app_config.defaults.allow_multiple_containers = allow_multiple_containers
    except Exception as e:
        click.secho(f"Error loading configuration: {e}", fg="red")
        raise click.Abort()
    
    # Determine log level based on flags and final config
    if quiet:
        effective_log_level = 'ERROR'
    elif verbose:
        effective_log_level = 'DEBUG'
    elif log_level is not None:
        effective_log_level = log_level
    else:
        # Use log level from the final resolved config
        effective_log_level =  None #app_config.advanced.log_level
    
    # Configure logging using the final config
    log_file_path = log_file_path if log_file_path is not None else user_config.log_file_path
    raw_logger = configure_logging(app_config, level=effective_log_level, log_file_path=log_file_path)
    
    # Ensure config directories exist now that we have a logger
    ensure_config_directories(app_config, raw_logger)
    
    # Store config and loggers in context for commands to access
    ctx.ensure_object(dict)
    ctx.obj['user_config'] = user_config
    ctx.obj['user_config_path'] = user_config_path
    ctx.obj['app_config'] = app_config
    ctx.obj['raw_logger'] = raw_logger  # For functions that need the actual logger
    ctx.obj['logger'] = get_safe_logger(raw_logger)  # Null-safe wrapper for commands

# Add all commands to the main CLI group
cli.add_command(up)
cli.add_command(down)
cli.add_command(config)
cli.add_command(dev)
cli.add_command(update)

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