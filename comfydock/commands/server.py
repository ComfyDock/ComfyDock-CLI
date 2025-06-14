import time
import click
import webbrowser
from comfydock_server.server import ComfyDockServer
from comfydock_server.config import AppConfig
from comfydock_core.docker_interface import DockerInterfaceConnectionError

from ..core.updates import check_for_updates, get_package_version
from ..utils.helpers import wait_for_frontend_ready

def create_server_with_error_handling(app_config: AppConfig, logger):
    """
    Create a ComfyDockServer instance with standardized error handling.
    
    Args:
        app_config: The application configuration
        logger: Logger for debug output
        
    Returns:
        ComfyDockServer instance
        
    Raises:
        click.Abort: If server creation fails
    """
    try:
        logger.debug(f"Initializing server with config: {app_config}")
        server = ComfyDockServer(app_config)
        logger.debug(f"Server created: {server}")
        return server
    except DockerInterfaceConnectionError:
        click.secho("\n" + "=" * 60, fg="red", bold=True)
        click.secho("  ❌ Docker Connection Error", fg="red", bold=True)
        click.secho("=" * 60, fg="red", bold=True)
        click.echo("  ComfyDock requires Docker to be running.")
        click.echo("")
        click.secho("  Please check:", fg="yellow")
        click.echo("    • Docker Desktop is installed and running")
        click.echo("    • Docker daemon is accessible")
        click.echo("")
        click.secho("  You can test Docker by running:", fg="green")
        click.secho("    docker --version", fg="cyan")
        click.echo("")
        click.secho("=" * 60, fg="red", bold=True)
        raise click.Abort()

@click.command()
@click.option("--backend", is_flag=True, help="Start only the backend server without the frontend")
@click.pass_context
def up(ctx, backend):
    """
    Start the ComfyDock server and the Docker-based frontend.

    This command uses the configuration loaded by the CLI, including any
    overrides from command-line arguments or config files.
    
    With --backend flag, only starts the backend server without the frontend.
    """
    # Get pre-configured objects from CLI context
    logger = ctx.obj['logger']  # Null-safe logger for this command
    app_config = ctx.obj['app_config']  # Fully configured AppConfig
    
    logger.info("Running 'comfydock up'...")
    
    # Check for updates at startup
    update_available, latest_version = check_for_updates(ctx.obj['raw_logger'])

    # Create server using standardized helper
    server = create_server_with_error_handling(app_config, logger)
    
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
        frontend_url = f"http://localhost:{app_config.frontend.default_host_port}"
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
        click.echo(f" Your version: v{get_package_version()}")
        click.echo("")
        click.echo(" To update, run:")
        click.secho("   pip install --upgrade comfydock", fg="green")
        click.secho("=" * 60 + "\n", fg="yellow", bold=True)

    # Print a nicely formatted message for the user
    click.secho("\n" + "=" * 60, fg="cyan", bold=True)
    click.secho(f"  {status_message}", fg="green", bold=True)

    # Always show backend URL using the new config structure
    click.secho(f"  Backend API:        http://{app_config.backend.host}:{app_config.backend.port}", fg="cyan")

    if not backend:
        click.secho(f"  Frontend UI:        http://localhost:{app_config.frontend.default_host_port}", fg="cyan")
    
    # Show the actual config file path used
    from ..core.config import DEFAULT_CONFIG_FILE
    default_config_file_path = ctx.obj['user_config_path'] if ctx.obj['user_config_path'] else DEFAULT_CONFIG_FILE
    click.secho(f"  Config File:        {str(default_config_file_path)}", fg="cyan")
    
    # Show file locations using actual configured paths
    # Convert Path objects to strings for display
    click.secho(f"  Environments:       {str(app_config.defaults.db_file_path)}", fg="cyan")
    click.secho(f"  User Settings:      {str(app_config.defaults.user_settings_file_path)}", fg="cyan")

    # Safely get log file path from logging config
    log_file_path = "Not configured"
    if hasattr(app_config.logging, '__root__'):
        handlers = app_config.logging.__root__.get('handlers', {})
        file_handler = handlers.get('file', {})
        log_file_path = file_handler.get('filename', 'Not configured')

    click.secho(f"  Log File:           {log_file_path}", fg="cyan")

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

@click.command()
@click.pass_context
def down(ctx):
    """
    Stop the running ComfyDock server (backend + frontend).
    
    If you started the server in another terminal, calling 'down' here attempts
    to stop the same environment.
    """
    # Get pre-configured objects from CLI context
    logger = ctx.obj['logger']  # Null-safe logger ready to use
    app_config = ctx.obj['app_config']  # Fully configured AppConfig
    logger.info("Running 'comfydock down'...")
        
    # Create server using standardized helper
    server = create_server_with_error_handling(app_config, logger)

    logger.info("Stopping ComfyDockServer (backend + frontend)...")
    server.stop()
    click.echo("Server has been stopped.")