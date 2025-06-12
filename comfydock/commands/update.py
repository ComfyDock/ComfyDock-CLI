import click
from ..core.config import load_config, save_config
from ..core.logging import configure_logging
from ..core.updates import check_for_updates, get_package_version

# For version checking
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

@click.command()
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
        click.echo(f"Current version: {get_package_version()}")
        click.echo(f"Latest version:  {latest_version}")
        click.echo("\nTo update, run:")
        click.secho("  pip install --upgrade comfydock", fg="cyan")
        click.echo("\nOr using uv tool:")
        click.secho("  uv tool install --upgrade comfydock", fg="cyan")
    else:
        click.secho(f"\n✓ You're using the latest version of ComfyDock CLI (v{get_package_version()}).", fg="green")