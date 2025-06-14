import click
from ..core.config import (
    save_config,
    CONFIG_FIELD_HELP, get_field_categories, get_all_user_configurable_fields,
    get_field_mapping
)
from ..core.logging import VALID_LOG_LEVELS

def _convert_value(val):
    """Convert user input from strings to appropriate types."""
    if isinstance(val, str):
        # Try boolean
        if val.lower() in ["true", "false"]:
            return val.lower() == "true"
        
        # Try integer
        try:
            return int(val)
        except ValueError:
            pass
    
    # Return as-is (string or already converted)
    return val

def _get_default_value_from_app_config(field_name: str, app_config) -> str:
    """Get the default value for a field from app_config."""
    from ..core.config import get_field_mapping
    
    field_mapping = get_field_mapping()
    if field_name not in field_mapping:
        return ""
    
    section, attribute, condition = field_mapping[field_name]
    
    try:
        section_obj = getattr(app_config, section)
        value = getattr(section_obj, attribute, None)
        return str(value) if value is not None else ""
    except (AttributeError, TypeError):
        return ""

@click.command()
@click.option("--list", "list_config", is_flag=True,
              help="List the current configuration values.")
@click.option("--all", "show_all", is_flag=True,
              help="Include all settings including advanced options.")
@click.option("--advanced", is_flag=True,
              help="Show or modify advanced configuration options.")
@click.argument("field", required=False)
@click.argument("value", required=False)
@click.pass_context
def config(ctx, list_config, show_all, advanced, field, value):
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
      backend_port, frontend_host_port,
      dockerhub_tags_url
    
    ADVANCED FIELDS (requires --advanced or --all):
    
      log_level (DEBUG, INFO, WARNING, ERROR, CRITICAL),
      check_for_updates, update_check_interval_days
    """
    logger = ctx.obj['logger']
    user_config_path = ctx.obj['user_config_path']
    user_config = ctx.obj['user_config']
    app_config = ctx.obj['app_config']  # Get app_config for default values
    
    # Get field categories from the mapping logic
    field_categories = get_field_categories()
    basic_fields = field_categories['basic']
    advanced_fields = field_categories['advanced']
    system_fields = field_categories['system']

    if list_config:
        click.echo("Current ComfyDock configuration:\n")
        
        # Display basic settings
        click.secho("Basic Settings:", fg="green", bold=True)
        for field_name in basic_fields:
            value = getattr(user_config, field_name, None)
            if value is not None:
                desc = CONFIG_FIELD_HELP.get(field_name, "")
                # Color code the field name and value
                click.echo(f"  ", nl=False)
                click.secho(f"{field_name}", fg="cyan", nl=False)
                click.echo(f" = ", nl=False)
                click.secho(f"{value}", fg="bright_white", bold=True)
                if desc:
                    click.secho(f"     -> {desc}", fg="bright_black")
        
        # Display advanced settings if requested
        if advanced or show_all:
            click.echo("\n")
            click.secho("Advanced Settings:", fg="blue", bold=True)
            for field_name in advanced_fields:
                value = getattr(user_config, field_name, None)
                if value is not None:
                    desc = CONFIG_FIELD_HELP.get(field_name, "")
                    # Color code the field name and value
                    click.echo(f"  ", nl=False)
                    click.secho(f"{field_name}", fg="cyan", nl=False)
                    click.echo(f" = ", nl=False)
                    click.secho(f"{value}", fg="bright_white", bold=True)
                    if desc:
                        click.secho(f"     -> {desc}", fg="bright_black")
        
        # Display system settings if requested
        if show_all:
            click.echo("\n")
            click.secho("System Settings (Read-Only):", fg="yellow", bold=True)
            for field_name in system_fields:
                value = getattr(user_config, field_name, None)
                if value is not None:
                    desc = CONFIG_FIELD_HELP.get(field_name, "")
                    # Color code the field name and value
                    click.echo(f"  ", nl=False)
                    click.secho(f"{field_name}", fg="cyan", nl=False)
                    click.echo(f" = ", nl=False)
                    click.secho(f"{value}", fg="bright_white", bold=True)
                    if desc:
                        click.secho(f"     -> {desc}", fg="bright_black")
        
        click.echo("")
        click.secho("Config file: ", fg="magenta", nl=False)
        click.secho(f"{user_config_path}", fg="bright_white", bold=True)
        return

    # If a user specified a field and value: set it directly
    if field and value:
        all_user_fields = get_all_user_configurable_fields()
        
        if field not in all_user_fields:
            if field in system_fields:
                click.secho(f"Error: '{field}' is managed automatically and cannot be changed.", fg="red")
            else:
                click.secho(f"Error: '{field}' is not a recognized config field.", fg="red")
                click.echo(f"Available fields: {', '.join(all_user_fields)}")
            return
        
        # Check if advanced field requires --advanced flag
        if field in advanced_fields and not advanced:
            click.secho(f"Error: '{field}' is an advanced setting. Use --advanced flag.", fg="red")
            return
        
        # Handle special validation for log_level
        if field == "log_level":
            value = value.upper()
            if value not in VALID_LOG_LEVELS:
                click.secho(f"Error: '{value}' is not a valid log level.", fg="red")
                click.echo(f"Valid levels are: {', '.join(VALID_LOG_LEVELS.keys())}")
                return
        
        # Convert the value to appropriate type
        converted_value = _convert_value(value)
        
        # Create updated config dict
        config_dict = user_config.model_dump(exclude_none=True)
        config_dict[field] = converted_value
        
        # Save the updated config
        try:
            save_config(config_dict, config_file_path=user_config_path, logger=logger.logger)
            click.secho(f"✓ Set '{field}' to '{converted_value}' in {user_config_path}", fg="green")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            click.secho(f"Error saving config: {e}", fg="red")
        return

    # Interactive mode: update fields one by one
    fields_to_edit = basic_fields.copy()
    if advanced or show_all:
        fields_to_edit.extend(advanced_fields)
    
    click.echo("Configure ComfyDock settings (press Enter to keep current values):")
    
    # Get current config as dict for easier manipulation
    config_dict = user_config.model_dump(exclude_none=True)
    updated = False
    
    for field_name in fields_to_edit:
        current_val = getattr(user_config, field_name, "")
        desc = CONFIG_FIELD_HELP.get(field_name, "")
        
        # Get default value from app_config if current value is empty
        if not current_val:
            default_val = _get_default_value_from_app_config(field_name, app_config)
        else:
            default_val = str(current_val)
        
        # Add special handling for log_level
        if field_name == "log_level":
            valid_options = ", ".join(VALID_LOG_LEVELS.keys())
            click.echo(f"\nLogging level ({valid_options}):")
        elif desc:
            click.echo(f"\n{desc}")
            
        new_val = click.prompt(f"{field_name}", default=default_val if default_val else "")
        
        # Skip if no change (compare with current value, not default)
        if str(new_val) == str(current_val):
            continue
            
        # Validate log_level if that's what's being set
        if field_name == "log_level":
            new_val = new_val.upper()
            if new_val not in VALID_LOG_LEVELS:
                click.secho(f"Warning: '{new_val}' is not a valid log level, keeping current value", fg="yellow")
                continue
                
        config_dict[field_name] = _convert_value(new_val)
        updated = True

    if updated:
        try:
            save_config(config_dict, config_file_path=user_config_path, logger=logger.logger)
            click.secho("\n✓ Configuration updated successfully!", fg="green")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            click.secho(f"\nError saving config: {e}", fg="red")
    else:
        click.echo("\nNo changes made.")