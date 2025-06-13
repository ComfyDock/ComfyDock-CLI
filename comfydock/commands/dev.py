import os
import click
from pathlib import Path
from ..core.config import (
    load_env_files, DOTENV_AVAILABLE, get_field_categories, 
    get_all_user_configurable_fields, get_all_mapped_fields,
    CONFIG_FIELD_HELP
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
@click.pass_context
def status(ctx):
    """Show current configuration with any developer overrides applied."""
    # Get pre-configured objects from CLI context
    logger = ctx.obj['logger']
    app_config = ctx.obj['app_config']
    user_config = ctx.obj['user_config']
    user_config_path = ctx.obj['user_config_path']
    
    # Load .env files for the check
    env_loaded = load_env_files()
    
    # Get field categories
    field_categories = get_field_categories()
    basic_fields = field_categories['basic']
    advanced_fields = field_categories['advanced']
    system_fields = field_categories['system']
    
    click.secho("ComfyDock Configuration Status:", fg="magenta", bold=True)
    
    if DOTENV_AVAILABLE:
        click.echo("\nEnvironment files:")
        if env_loaded:
            click.secho("  .env files were loaded", fg="green")
        else:
            click.echo("  No .env files found")
    else:
        click.secho("\nNote: Install python-dotenv to use .env files", fg="yellow")
        click.echo("  pip install python-dotenv")
    
    click.echo(f"\nConfig file: {user_config_path}")
    
    click.echo("\nBasic User Settings:")
    for field_name in basic_fields:
        value = getattr(user_config, field_name, None)
        if value is not None:
            click.echo(f"  {field_name} = {value}")
        else:
            click.secho(f"  {field_name} = <not set>", dim=True)
    
    click.echo("\nAdvanced Settings:")
    for field_name in advanced_fields:
        value = getattr(user_config, field_name, None)
        if value is not None:
            click.echo(f"  {field_name} = {value}")
        else:
            click.secho(f"  {field_name} = <not set>", dim=True)
    
    click.echo("\nSystem Settings (Auto-managed):")
    for field_name in system_fields:
        value = getattr(user_config, field_name, None)
        if value is not None:
            click.echo(f"  {field_name} = {value}")
        else:
            click.secho(f"  {field_name} = <not set>", dim=True)
    
    click.echo("\nFinal AppConfig Values:")
    click.echo(f"  Backend: {app_config.backend.host}:{app_config.backend.port}")
    click.echo(f"  Frontend: localhost:{app_config.frontend.default_host_port}")
    click.echo(f"  ComfyUI Path: {app_config.defaults.comfyui_path}")
    click.echo(f"  DB File: {app_config.defaults.db_file_path}")
    click.echo(f"  User Settings: {app_config.defaults.user_settings_file_path}")
    click.echo(f"  Log Level: {app_config.advanced.log_level}")
    
    click.echo("\nDeveloper Environment Variables:")
    env_vars_found = False
    all_fields = get_all_mapped_fields()
    for field_name in all_fields:
        env_var_name = f"COMFYDOCK_{field_name.upper()}"
        if env_var_name in os.environ:
            click.secho(f"  {env_var_name}={os.environ[env_var_name]}", fg="yellow")
            env_vars_found = True
    
    if not env_vars_found:
        click.echo("  No COMFYDOCK_* environment variables found")

@dev.command()
def env_setup():
    """Generate template .env files for development overrides."""
    if not DOTENV_AVAILABLE:
        click.secho("Error: python-dotenv package is not installed.", fg="red", bold=True)
        click.echo("Install it with: pip install python-dotenv")
        return
    
    # Get all configurable fields
    field_categories = get_field_categories()
    all_fields = field_categories['basic'] + field_categories['advanced'] + field_categories['system']
    
    # Create .env template with all configurable settings
    env_file = Path.cwd() / ".env"
    if not env_file.exists() or click.confirm(f"{env_file} already exists. Overwrite?"):
        with open(env_file, "w") as f:
            f.write("# ComfyDock Development Environment\n")
            f.write("# This file can be checked into git with default values.\n")
            f.write("# Uncomment any variables you want to override.\n\n")
            
            # Group by category
            f.write("# Basic Settings\n")
            for field_name in field_categories['basic']:
                help_text = CONFIG_FIELD_HELP.get(field_name, "")
                if help_text:
                    f.write(f"# {help_text}\n")
                f.write(f"# COMFYDOCK_{field_name.upper()}=\n\n")
            
            f.write("# Advanced Settings\n")
            for field_name in field_categories['advanced']:
                help_text = CONFIG_FIELD_HELP.get(field_name, "")
                if help_text:
                    f.write(f"# {help_text}\n")
                f.write(f"# COMFYDOCK_{field_name.upper()}=\n\n")
            
            f.write("# System Settings (normally auto-managed)\n")
            for field_name in field_categories['system']:
                help_text = CONFIG_FIELD_HELP.get(field_name, "")
                if help_text:
                    f.write(f"# {help_text}\n")
                f.write(f"# COMFYDOCK_{field_name.upper()}=\n\n")
        
        click.secho(f"Created {env_file}", fg="green")
        click.echo("Uncomment any variables you want to override.")
    
    # Create .env.local template
    env_local_file = Path.cwd() / ".env.local"
    if not env_local_file.exists() or click.confirm(f"{env_local_file} already exists. Overwrite?"):
        with open(env_local_file, "w") as f:
            f.write("# ComfyDock Local Development Environment\n")
            f.write("# This file should NOT be checked into git.\n")
            f.write("# These values will take precedence over .env file values.\n\n")
            
            f.write("# Example overrides for local development:\n")
            f.write("# COMFYDOCK_BACKEND_PORT=5173\n")
            f.write("# COMFYDOCK_FRONTEND_HOST_PORT=8001\n")
            f.write("# COMFYDOCK_LOG_LEVEL=DEBUG\n")
            f.write("# COMFYDOCK_COMFYUI_PATH=/path/to/your/ComfyUI\n\n")
            
            f.write("# Add your local overrides below:\n")
        
        click.secho(f"Created {env_local_file}", fg="green")
        click.echo("Add your local development overrides to this file.")
    
    # Add .env.local to .gitignore if it exists
    gitignore_file = Path.cwd() / ".gitignore"
    if gitignore_file.exists():
        with open(gitignore_file, "r") as f:
            content = f.read()
        
        if ".env.local" not in content:
            with open(gitignore_file, "a") as f:
                f.write("\n# Local development environment\n.env.local\n")
            click.secho("Added .env.local to .gitignore", fg="green")
    else:
        click.secho("No .gitignore found - consider adding .env.local to your .gitignore", fg="yellow")

@dev.command()
@click.pass_context
def config_info(ctx):
    """Show detailed information about the configuration system."""
    field_categories = get_field_categories()
    
    click.secho("ComfyDock Configuration System Info:", fg="magenta", bold=True)
    
    click.echo(f"\nField Categories:")
    click.secho(f"  Basic fields ({len(field_categories['basic'])}): ", fg="green", nl=False)
    click.echo(", ".join(field_categories['basic']))
    
    click.secho(f"  Advanced fields ({len(field_categories['advanced'])}): ", fg="blue", nl=False)
    click.echo(", ".join(field_categories['advanced']))
    
    click.secho(f"  System fields ({len(field_categories['system'])}): ", fg="yellow", nl=False)
    click.echo(", ".join(field_categories['system']))
    
    click.echo(f"\nTotal configurable fields: {len(get_all_user_configurable_fields())}")
    click.echo(f"Total mapped fields: {len(get_all_mapped_fields())}")
    
    click.echo(f"\nConfiguration precedence (highest to lowest):")
    click.echo("  1. CLI arguments (--backend-port, etc.)")
    click.echo("  2. Environment variables (COMFYDOCK_*)")
    click.echo("  3. User config file (~/.comfydock/config.json)")
    click.echo("  4. CLI defaults (cli_defaults.json)")
    click.echo("  5. Server defaults (default_config.json)")