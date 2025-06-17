import logging
import os
from pathlib import Path
from comfydock_server.config import AppConfig

# Valid logging levels
VALID_LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

class NullSafeLogger:
    """A logger wrapper that handles None loggers gracefully."""
    
    def __init__(self, logger=None):
        self.logger = logger
    
    def debug(self, msg, *args, **kwargs):
        if self.logger:
            self.logger.debug(msg, *args, **kwargs)
    
    def info(self, msg, *args, **kwargs):
        if self.logger:
            self.logger.info(msg, *args, **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        if self.logger:
            self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        if self.logger:
            self.logger.error(msg, *args, **kwargs)
    
    def critical(self, msg, *args, **kwargs):
        if self.logger:
            self.logger.critical(msg, *args, **kwargs)

def get_safe_logger(logger=None):
    """Get a null-safe logger wrapper."""
    return NullSafeLogger(logger)

def configure_logging(app_config: AppConfig, level=None, log_file_path=None):
    """
    Configure logging using the config from app_config.logging.__root__.
    Optionally override level values with the provided level parameter.
    
    Args:
        app_config: The application configuration containing logging settings
        level: Optional log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               If provided, overrides all level settings in the logging config.
        log_file_path: Optional path to the log file. If provided, overrides the
                      default filename in the file handler configuration.
    
    Returns:
        The configured root logger
    """
    # Get the logging config dict
    logging_config = app_config.logging.__root__.copy()
    
    # If a log file path is provided, override the file handler filename
    if log_file_path is not None and 'handlers' in logging_config and 'file' in logging_config['handlers']:
        logging_config['handlers']['file']['filename'] = log_file_path
    
    # Expand tilde in log file path and ensure directory exists
    if 'handlers' in logging_config and 'file' in logging_config['handlers']:
        file_path = logging_config['handlers']['file']['filename']
        if file_path:
            # Always expand tilde if present
            if '~' in file_path:
                file_path = os.path.expanduser(file_path)
                logging_config['handlers']['file']['filename'] = file_path
            
            # Always ensure the directory exists
            log_dir = os.path.dirname(file_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
    
    # If a level is provided, override all level settings in the config
    if level is not None:
        # Override root logger level
        if 'root' in logging_config:
            logging_config['root']['level'] = level
        
        # Override handler levels
        if 'handlers' in logging_config:
            # Set the file handler level
            for handler_name, handler_config in logging_config['handlers'].items():
                handler_config['level'] = level
        
        # Override individual logger levels
        if 'loggers' in logging_config:
            for logger_name, logger_config in logging_config['loggers'].items():
                logger_config['level'] = level
    
    # Always keep uvicorn logging at INFO or higher to prevent verbose output
    # even when overall level is DEBUG
    if 'loggers' not in logging_config:
        logging_config['loggers'] = {}
    
    # Ensure uvicorn logger exists and is set to INFO
    if 'uvicorn' not in logging_config['loggers']:
        logging_config['loggers']['uvicorn'] = {
            'handlers': ['file'] if 'file' in logging_config.get('handlers', {}) else [],
            'level': 'INFO',
            'propagate': False
        }
    else:
        # Override uvicorn level to INFO even if global level is DEBUG
        logging_config['loggers']['uvicorn']['level'] = 'INFO'
    
    # Also handle uvicorn.access and uvicorn.error loggers
    for uvicorn_logger in ['uvicorn.access', 'uvicorn.error']:
        if uvicorn_logger not in logging_config['loggers']:
            logging_config['loggers'][uvicorn_logger] = {
                'handlers': ['file'] if 'file' in logging_config.get('handlers', {}) else [],
                'level': 'INFO',
                'propagate': False
            }
        else:
            logging_config['loggers'][uvicorn_logger]['level'] = 'INFO'
    
    # Apply the logging configuration
    logging.config.dictConfig(logging_config)
    
    # Get and return the root logger
    logger = logging.getLogger()
    
    # Set the root logger level
    # logger.setLevel(level)
    
    # Remove the console handler
    for handler in logger.handlers:
        if handler.name == 'console':
            logger.removeHandler(handler)
    
    return logger