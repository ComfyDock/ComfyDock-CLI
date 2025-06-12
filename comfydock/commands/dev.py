import os
import click
from pathlib import Path
from ..core.config import (
    load_env_files, get_complete_config, load_config, 
    CONFIGURABLE_CONFIG, NON_CONFIGURABLE_CONFIG, DOTENV_AVAILABLE
)

@click.group()
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