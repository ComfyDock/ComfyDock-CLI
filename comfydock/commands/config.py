import click
from ..core.config import (
    load_config, save_config, get_complete_config, CONFIG_FILE,
    CONFIGURABLE_CONFIG, ADVANCED_CONFIG, NON_CONFIGURABLE_CONFIG,
    CONFIG_FIELD_HELP, _convert_value
)
from ..core.logging import configure_logging, VALID_LOG_LEVELS

@click.command()
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