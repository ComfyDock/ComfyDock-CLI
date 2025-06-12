import time
from typing import Optional, Any
import click

# For web requests
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

def wait_for_frontend_ready(url: str, logger, timeout: int = 30, check_interval: float = 1.0) -> bool:
    """
    Wait for the frontend to be ready by polling the URL.
    
    Args:
        url: The URL to check
        logger: Logger instance
        timeout: Maximum time to wait in seconds
        check_interval: Time between checks in seconds
        
    Returns:
        bool: True if frontend is ready, False if timed out
    """
    logger.info(f"Waiting for frontend at {url} to be ready (timeout: {timeout}s)")
    
    if not REQUESTS_AVAILABLE:
        logger.warning("Requests package not available, cannot check if frontend is ready")
        # If we can't check, wait a reasonable time then assume it's ready
        time.sleep(5)
        return True
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Try to connect to the frontend
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                logger.info(f"Frontend is ready after {time.time() - start_time:.1f} seconds")
                return True
        except requests.RequestException:
            # Expected during startup, not an error
            pass
        
        # Wait a bit before trying again
        time.sleep(check_interval)
    
    logger.warning(f"Timeout ({timeout}s) waiting for frontend to be ready")
    return False


def parse_str_with_default(default: str):
    """Create a Click callback that returns default for templated env variables."""
    def callback(ctx, param, value):
        del ctx, param  # Unused parameters
        if value is None:
            return None
        if value.startswith("{{env.") and value.endswith("}}"):
            return default
        return value
    return callback


def parse_int_with_default(default: int):
    """Create a Click callback that returns default for templated env variables."""
    def callback(ctx, param, value):
        del ctx, param  # Unused parameters
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            if isinstance(value, str) and value.startswith("{{env.") and value.endswith("}}"):
                return default
            raise click.BadParameter(f"Invalid int value: {value}")
    return callback


def parse_bool_with_default(default: bool):
    """Create a Click callback that returns default for templated env variables."""
    def callback(ctx, param, value):
        del ctx, param  # Unused parameters
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            if value.startswith("{{env.") and value.endswith("}}"):
                return default
            val = value.lower()
            if val in ["true", "1", "yes"]:
                return True
            elif val in ["false", "0", "no"]:
                return False
        raise click.BadParameter(f"Invalid bool value: {value}")
    return callback