import logging
from logging.handlers import RotatingFileHandler
from .config import CONFIG_DIR, load_config

# Valid logging levels
VALID_LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

def configure_logging():
    """
    Configure logging to write to a rotating log file.
    Uses the configured log level from settings.
    """
    from .config import ensure_config_dir_and_file
    ensure_config_dir_and_file()
    
    # Get the config to read log_level
    cfg_data = load_config()
    log_level_str = cfg_data.get("log_level", "INFO").upper()
    
    # Validate log level and convert to int
    if log_level_str not in VALID_LOG_LEVELS:
        log_level_str = "INFO"  # Default if invalid
    
    log_level = VALID_LOG_LEVELS[log_level_str]
    
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Remove any existing handlers so we don't print to console
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    log_file_path = CONFIG_DIR / "comfydock.log"

    # Set up rotating file handler
    file_handler = RotatingFileHandler(
        filename=str(log_file_path),
        maxBytes=20 * 1024 * 1024,  # ~20MB
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    
    # Set up formatter for human-readable messages
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Add the handler to the logger
    logger.addHandler(file_handler)
    
    logger.info(f"Logging initialized with level {log_level_str}")
    
    return logger