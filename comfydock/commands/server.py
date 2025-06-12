import time
import click
import webbrowser
from comfydock_server.server import ComfyDockServer
from comfydock_server.config import AppConfig, load_config
from comfydock_core.docker_interface import DockerInterfaceConnectionError

from ..core.config import get_server_config, get_complete_config, load_config as cli_load_config
from ..core.logging import configure_logging
from ..core.updates import check_for_updates, get_package_version
from ..utils.helpers import wait_for_frontend_ready, parse_str_with_default, parse_int_with_default, parse_bool_with_default

@click.command()
@click.option("--backend", is_flag=True, help="Start only the backend server without the frontend")
@click.option("--comfyui-path", type=str, help="Path to ComfyUI installation")
@click.option("--db-file-path", type=str, help="Path to environments database file")
@click.option("--user-settings-file-path", type=str, help="Path to user settings file")
@click.option("--backend-port", type=int, help="Backend server port")
@click.option("--frontend-host-port", type=int, help="Frontend host port")
@click.option("--allow-multiple-containers", type=bool, help="Allow running multiple containers")
def up(backend, comfyui_path, db_file_path, user_settings_file_path, backend_port, frontend_host_port, allow_multiple_containers):
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

    # Collect CLI overrides for AppConfig structure
    cli_overrides = {}
    
    if backend_port is not None:
        cli_overrides.setdefault('backend', {})['port'] = backend_port
    if frontend_host_port is not None:
        cli_overrides.setdefault('frontend', {})['default_host_port'] = frontend_host_port
    
    # Map to defaults section
    defaults_overrides = {}
    if comfyui_path is not None:
        defaults_overrides['comfyui_path'] = comfyui_path
    if db_file_path is not None:
        defaults_overrides['db_file_path'] = db_file_path
    if user_settings_file_path is not None:
        defaults_overrides['user_settings_file_path'] = user_settings_file_path
    if allow_multiple_containers is not None:
        defaults_overrides['allow_multiple_containers'] = allow_multiple_containers
    
    if defaults_overrides:
        cli_overrides['defaults'] = defaults_overrides

    # Load config using the server's load_config function
    try:
        app_config = load_config(cli_overrides=cli_overrides)
    except Exception as e:
        click.secho(f"Error loading configuration: {e}", fg="red")
        raise click.Abort()

    # Create and start the server
    try:
        server = ComfyDockServer(app_config)
    except DockerInterfaceConnectionError:
        click.secho("\n" + "=" * 60, fg="red", bold=True)
        click.secho("  ❌ Docker Connection Error", fg="red", bold=True)
        click.secho("=" * 60, fg="red", bold=True)
        click.echo("  ComfyDock requires Docker to be running to start the server.")
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
def down():
    """
    Stop the running ComfyDock server (backend + frontend).
    
    If you started the server in another terminal, calling 'down' here attempts
    to stop the same environment.
    """
    logger = configure_logging()
    logger.info("Running 'comfydock down'...")

    # Load config using the server's load_config function
    try:
        app_config = load_config()
    except Exception as e:
        click.secho(f"Error loading configuration: {e}", fg="red")
        raise click.Abort()
        
    try:
        server = ComfyDockServer(app_config)
    except DockerInterfaceConnectionError:
        click.secho("\n" + "=" * 60, fg="red", bold=True)
        click.secho("  ❌ Docker Connection Error", fg="red", bold=True)
        click.secho("=" * 60, fg="red", bold=True)
        click.echo("  ComfyDock requires Docker to be running to stop the server.")
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

    logger.info("Stopping ComfyDockServer (backend + frontend)...")
    server.stop()
    click.echo("Server has been stopped.")