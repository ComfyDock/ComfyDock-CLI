import time
from typing import Tuple
from .config import load_config, save_config, UserEditableConfig

# For version checking
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# For package version detection
try:
    from importlib.metadata import version as get_version
    PACKAGE_VERSION = get_version("comfydock")
except (ImportError, ModuleNotFoundError):
    # Either importlib.metadata is not available (Python < 3.8)
    # or the package is not installed (development mode)
    try:
        # Fallback to pkg_resources for Python < 3.8
        from pkg_resources import get_distribution
        PACKAGE_VERSION = get_distribution("comfydock").version
    except (ImportError, ModuleNotFoundError):
        # If all else fails, use frontend version as a fallback
        PACKAGE_VERSION = "0.1.0"  # Default development version

def check_for_updates(logger) -> Tuple[bool, str]:
    """
    Check if a newer version of comfydock_cli is available on PyPI.
    
    Returns:
        Tuple of (update_available, latest_version)
    """
    if not REQUESTS_AVAILABLE:
        logger.warning("Cannot check for updates: requests package not installed")
        return False, ""
    
    try:
        # Load config to get update settings
        cfg_data: UserEditableConfig = load_config()
        if not cfg_data.check_for_updates:
            logger.debug("Update checking is disabled in config")
            return False, ""
        
        # Check if we've checked recently
        last_check = cfg_data.last_update_check
        interval_days = cfg_data.update_check_interval_days
        now = int(time.time())
        
        # If we checked less than interval_days ago, skip the check
        if last_check > 0:
            next_check_time = last_check + (interval_days * 86400)  # 86400 seconds in a day
            if now < next_check_time:
                logger.debug(f"Skipping update check (last check: {last_check}, next: {next_check_time})")
                return False, ""
        
        # Update the last check timestamp
        cfg_data.last_update_check = now
        save_config(cfg_data.model_dump(), logger=logger)
        
        # Query PyPI for the latest version
        logger.debug("Checking for new version on PyPI")
        response = requests.get(
            "https://pypi.org/pypi/comfydock/json",
            timeout=5,  # 5 second timeout
        )
        
        if response.status_code != 200:
            logger.warning(f"Failed to check for updates: HTTP {response.status_code}")
            return False, ""
        
        data = response.json()
        latest_version = data["info"]["version"]
        
        # Parse and compare versions
        from packaging import version as pkg_version
        current = pkg_version.parse(PACKAGE_VERSION)
        latest = pkg_version.parse(latest_version)
        
        if latest > current:
            logger.info(f"New version available: {latest_version} (current: {PACKAGE_VERSION})")
            return True, latest_version
        
        logger.debug(f"Current version {PACKAGE_VERSION} is up to date")
        return False, ""
        
    except Exception as e:
        logger.warning(f"Error checking for updates: {str(e)}")
        return False, ""

def get_package_version() -> str:
    """Get the current package version."""
    return PACKAGE_VERSION