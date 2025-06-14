import os
import json
from pathlib import Path
from typing import Optional, Union
from pydantic import BaseModel
from comfydock_server.config import AppConfig

# Add python-dotenv for .env file support
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

# --------------------------------------------------
# Constants and defaults
# --------------------------------------------------

# The directory in the user's home folder to store config, DB, etc.
CONFIG_DIR = Path.home() / ".comfydock"
DEFAULT_CONFIG_FILE = CONFIG_DIR / "config.json"

# Pydantic model for the config
class UserEditableConfig(BaseModel):
    comfyui_path: Optional[str] = None
    db_file_path: Optional[str] = None
    user_settings_file_path: Optional[str] = None
    backend_port: Optional[int] = None
    backend_host: Optional[str] = None
    frontend_image: Optional[str] = None
    frontend_container_name: Optional[str] = None
    frontend_container_port: Optional[int] = None
    frontend_host_port: Optional[int] = None
    dockerhub_tags_url: Optional[str] = None
    log_level: Optional[str] = None
    log_file_path: Optional[str] = None
    check_for_updates: Optional[bool] = None
    update_check_interval_days: Optional[int] = None
    last_update_check: Optional[int] = None


# Help text for each field (used in 'comfydock config')
CONFIG_FIELD_HELP = {
    "comfyui_path": "Default filesystem path to your local ComfyUI clone or desired location.",
    "db_file_path": "Where to store known Docker environments (JSON).",
    "user_settings_file_path": "Where to store user preferences for ComfyDock. (JSON)",
    "backend_port": "TCP port for the backend FastAPI server.",
    "frontend_host_port": "TCP port on your local machine for accessing the frontend.",
    "dockerhub_tags_url": "URL to the Docker Hub API endpoint for retrieving available tags.",
    
    # Advanced settings
    "log_level": "Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL).",
    "log_file_path": "Path to the log file (defaults to ~/.comfydock/comfydock.log).",
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

def get_field_mapping():
    """
    Define the mapping from UserEditableConfig fields to AppConfig locations.
    This centralizes the mapping logic for both the actual mapping function and field categories.
    
    Returns:
        dict: Mapping of field names to (section, attribute, condition_check) tuples
    """
    return {
        # Defaults section mappings
        'comfyui_path': ('defaults', 'comfyui_path', 'truthy'),
        'db_file_path': ('defaults', 'db_file_path', 'truthy'),
        'user_settings_file_path': ('defaults', 'user_settings_file_path', 'truthy'),
        'dockerhub_tags_url': ('defaults', 'dockerhub_tags_url', 'truthy'),
        
        # Advanced section mappings
        'log_level': ('advanced', 'log_level', 'truthy'),
        'check_for_updates': ('advanced', 'check_for_updates', 'not_none'),
        'update_check_interval_days': ('advanced', 'update_check_interval_days', 'not_none'),
        
        # Backend section mappings
        'backend_port': ('backend', 'port', 'not_none'),
        'backend_host': ('backend', 'host', 'truthy'),
        
        # Frontend section mappings
        'frontend_image': ('frontend', 'image', 'truthy'),
        'frontend_container_name': ('frontend', 'container_name', 'truthy'),
        'frontend_container_port': ('frontend', 'container_port', 'truthy'),
        'frontend_host_port': ('frontend', 'default_host_port', 'not_none'),
    }

def load_config(config_file_path: str = DEFAULT_CONFIG_FILE, logger=None) -> UserEditableConfig:
    """Load config from ~/.comfydock/config.json, creating defaults if necessary."""
    # ensure_config_dir_and_file()
    cfg_data = None
    try:
        with open(config_file_path, "r", encoding="utf-8") as f:
            cfg_data = json.load(f)
    except Exception as e:
        if logger:
            logger.error(f"Error loading config from {config_file_path}: {e}")
        return UserEditableConfig()  # Return empty UserEditableConfig instead of {}
        
    if cfg_data is None:
        if logger:
            logger.error(f"Config data is None for {config_file_path}")
        return UserEditableConfig()  # Return empty UserEditableConfig instead of {}

    # return schema_config
    return UserEditableConfig(**cfg_data)

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

def load_env_overrides() -> UserEditableConfig:
    """
    Load environment variable overrides with COMFYDOCK_ prefix.
    Returns a UserEditableConfig with only the overridden values set.
    """
    env_overrides = {}
    
    # Get all possible field names from the model
    all_fields = UserEditableConfig.model_fields.keys()
    
    for field_name in all_fields:
        env_var_name = f"COMFYDOCK_{field_name.upper()}"
        env_value = os.environ.get(env_var_name)
        
        if env_value is not None:
            # Convert string values to appropriate types
            field_info = UserEditableConfig.model_fields[field_name]
            field_type = field_info.annotation
            
            # Handle Optional types (extract the inner type)
            if hasattr(field_type, '__origin__') and field_type.__origin__ is Union:
                # For Optional[T], get T (the non-None type)
                inner_types = [t for t in field_type.__args__ if t is not type(None)]
                if inner_types:
                    field_type = inner_types[0]
            
            # Convert the environment variable value to the correct type
            try:
                if field_type == bool:
                    # Handle boolean conversion
                    converted_value = env_value.lower() in ('true', '1', 'yes', 'on')
                elif field_type == int:
                    converted_value = int(env_value)
                elif field_type == str:
                    converted_value = env_value
                else:
                    # Default to string for unknown types
                    converted_value = env_value
                    
                env_overrides[field_name] = converted_value
                
            except (ValueError, TypeError) as e:
                # Skip invalid values but could log a warning
                continue
    
    return UserEditableConfig(**env_overrides)

def save_config(cfg_data, config_file_path: str = DEFAULT_CONFIG_FILE, logger=None):
    """Save config data back to ~/.comfydock/config.json."""
    try:
        with open(config_file_path, "w", encoding="utf-8") as f:
            json.dump(cfg_data, f, indent=4)
    except Exception as e:
        if logger:
            logger.error(f"Error saving config to {config_file_path}: {e}")
        raise e

def get_field_categories():
    """
    Derive field categories from the field mapping.
    This ensures the config command stays in sync with the actual mapping.
    
    Returns:
        dict: Field categories with 'basic', 'advanced', and 'system' keys
    """
    field_mapping = get_field_mapping()
    
    # Group fields by their target section in AppConfig
    defaults_fields = []
    advanced_fields = []
    backend_fields = []
    frontend_fields = []
    
    for field_name, (section, attribute, condition) in field_mapping.items():
        if section == 'defaults':
            defaults_fields.append(field_name)
        elif section == 'advanced':
            advanced_fields.append(field_name)
        elif section == 'backend':
            backend_fields.append(field_name)
        elif section == 'frontend':
            frontend_fields.append(field_name)
    
    # Combine defaults and network fields as "basic" user-configurable settings
    basic_fields = defaults_fields + backend_fields + ['frontend_host_port', 'log_file_path']
    
    # System fields are frontend fields that aren't user-configurable basics
    system_fields = [f for f in frontend_fields if f != 'frontend_host_port']
    
    # Add any unmapped fields from UserEditableConfig as system fields
    all_model_fields = set(UserEditableConfig.model_fields.keys())
    all_mapped_fields = set(field_mapping.keys())
    unmapped_fields = all_model_fields - all_mapped_fields
    system_fields.extend(list(unmapped_fields))
    
    return {
        'basic': basic_fields,
        'advanced': advanced_fields,
        'system': system_fields
    }

def map_user_config_to_app_config(user_config: UserEditableConfig, app_config: AppConfig) -> AppConfig:
    """
    Maps fields from UserEditableConfig to the appropriate locations in AppConfig.
    Only updates fields that are present in user_config, preserving app_config defaults for others.
    
    Args:
        user_config: The user's configuration loaded from config.json
        app_config: The AppConfig instance to update
        
    Returns:
        The updated AppConfig instance
    """
    field_mapping = get_field_mapping()
    
    for field_name, (section, attribute, condition) in field_mapping.items():
        value = getattr(user_config, field_name, None)
        
        # Apply the appropriate condition check
        should_map = False
        if condition == 'truthy' and value:
            should_map = True
        elif condition == 'not_none' and value is not None:
            should_map = True
            
        if should_map:
            # Get the section object (e.g., app_config.defaults, app_config.advanced)
            section_obj = getattr(app_config, section)
            # Set the attribute on that section
            setattr(section_obj, attribute, value)
    
    return app_config

def get_all_user_configurable_fields():
    """Get all fields that users can configure (basic + advanced)."""
    categories = get_field_categories()
    return categories['basic'] + categories['advanced']

def get_all_mapped_fields():
    """Get all fields that are mapped in the UserEditableConfig model."""
    return list(UserEditableConfig.model_fields.keys())

def merge_user_configs(base_config: UserEditableConfig, override_config: UserEditableConfig) -> UserEditableConfig:
    """
    Merge two UserEditableConfig instances, with override_config taking precedence.
    Only non-None values from override_config will override base_config values.
    
    Args:
        base_config: The base configuration (lower precedence)
        override_config: The override configuration (higher precedence)
        
    Returns:
        A new UserEditableConfig with merged values
    """
    # Convert both configs to dicts, excluding None values
    base_dict = base_config.model_dump(exclude_none=True)
    override_dict = override_config.model_dump(exclude_none=True)
    
    # Merge the dictionaries (override takes precedence)
    merged_dict = {**base_dict, **override_dict}
    
    return UserEditableConfig(**merged_dict)