import os
import click
import subprocess
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

@dev.command()
@click.option("--shell", default="/bin/bash", help="Shell to use (default: /bin/bash)")
@click.option("--container", help="Container name or ID to exec into (skips selection)")
@click.option("--user", help="User to exec as (e.g., 'comfy', 'root'). Defaults to container's default user")
def exec(shell, container, user):
    """Execute into a running Docker container's shell.
    
    Lists running containers and allows you to choose one to exec into.
    Defaults to ComfyUI containers (comfy-env-*) if available.
    """
    try:
        # Get list of running containers - use simpler format without table header
        result = subprocess.run([
            "docker", "ps", "--format", 
            r"{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}"
        ], capture_output=True, text=True, check=True)
        
        if not result.stdout.strip():
            click.secho("No running Docker containers found.", fg="yellow")
            return
            
        lines = result.stdout.strip().split('\n')
        
        # Parse container information
        containers = []
        for line in lines:
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 4:
                    containers.append({
                        'id': parts[0].strip(),
                        'name': parts[1].strip(),
                        'image': parts[2].strip(),
                        'status': parts[3].strip()
                    })
        
        if not containers:
            click.secho("No running Docker containers found.", fg="yellow")
            return
            
        # If container specified, use it directly
        if container:
            selected_container = None
            for c in containers:
                if container in (c['id'], c['name']) or container in c['id']:
                    selected_container = c
                    break
                    
            if not selected_container:
                click.secho(f"Container '{container}' not found in running containers.", fg="red")
                return
        else:
            # Sort containers to prioritize ComfyUI containers
            def sort_key(c):
                name = c['name'].lower()
                if 'comfy-env-' in name:
                    return (0, name)  # Highest priority
                elif 'comfy' in name:
                    return (1, name)  # Second priority
                else:
                    return (2, name)  # Lowest priority
                    
            containers.sort(key=sort_key)
            
            # Display containers
            click.secho("Running Docker containers:", fg="cyan", bold=True)
            click.echo()
            
            for i, c in enumerate(containers, 1):
                # Highlight ComfyUI containers
                if 'comfy' in c['name'].lower():
                    click.secho(f"  {i}. ", fg="green", nl=False, bold=True)
                    click.secho(f"{c['name']}", fg="green", bold=True, nl=False)
                    click.echo(f" ({c['id'][:12]}) - {c['image']}")
                else:
                    click.echo(f"  {i}. {c['name']} ({c['id'][:12]}) - {c['image']}")
            
            click.echo()
            
            # Auto-select first ComfyUI container if available
            default_choice = 1
            if containers and 'comfy' in containers[0]['name'].lower():
                click.secho(f"Default: {containers[0]['name']} (ComfyUI container detected)", fg="green")
            
            # Get user choice
            try:
                choice = click.prompt(
                    "Select container to exec into", 
                    type=int, 
                    default=default_choice,
                    show_default=True
                )
                
                if choice < 1 or choice > len(containers):
                    click.secho("Invalid selection.", fg="red")
                    return
                    
                selected_container = containers[choice - 1]
                
            except (click.Abort, KeyboardInterrupt):
                click.echo("\nAborted.")
                return
        
        # Execute into the selected container
        container_name = selected_container['name']
        container_id = selected_container['id']
        
        click.secho(f"\nExecuting into container: {container_name}", fg="green")
        if user:
            click.secho(f"As user: {user}", fg="cyan")
        click.secho(f"Using shell: {shell}", fg="cyan")
        click.echo("Type 'exit' to return to your host shell.\n")
        
        # Build docker exec command with optional user
        cmd_parts = ["docker", "exec", "-it"]
        if user:
            cmd_parts.extend(["--user", user])
        cmd_parts.extend([container_id, shell])
        
        # Use os.system for interactive shell (join command parts)
        cmd = " ".join(cmd_parts)
        exit_code = os.system(cmd)
        
        if exit_code != 0:
            click.secho(f"\nCommand exited with code {exit_code}", fg="yellow")
        else:
            click.secho("\nExited container shell.", fg="green")
            
    except subprocess.CalledProcessError as e:
        click.secho(f"Error running docker command: {e}", fg="red")
        click.echo("Make sure Docker is running and you have permission to use it.")
    except FileNotFoundError:
        click.secho("Docker command not found. Please install Docker.", fg="red")
    except Exception as e:
        click.secho(f"Unexpected error: {e}", fg="red")