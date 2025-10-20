"""
Logging configuration for RunPod ComfyUI Serverless Handler
"""
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional


class ComfyUILogger:
    """Centralized logging for ComfyUI Serverless Handler"""

    def __init__(self):
        self.logger = logging.getLogger('comfyui-serverless')
        self._setup_logging()

    def _setup_logging(self):
        """Setup logging configuration"""
        # Clear existing handlers
        self.logger.handlers.clear()

        # Set log level
        log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper(), logging.INFO)

        # Create formatter
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Console handler (always enabled)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        self.logger.addHandler(console_handler)

        # File handler (if LOG_FILE is configured)
        log_file = os.getenv('LOG_FILE')
        if log_file:
            try:
                log_path = Path(log_file)
                log_path.parent.mkdir(parents=True, exist_ok=True)

                # Use rotating file handler to prevent log files from growing too large
                file_handler = logging.handlers.RotatingFileHandler(
                    log_file,
                    maxBytes=10*1024*1024,  # 10MB
                    backupCount=5
                )
                file_handler.setFormatter(formatter)
                file_handler.setLevel(log_level)
                self.logger.addHandler(file_handler)
            except Exception as e:
                # Fallback to console logging if file logging fails
                print(f"Warning: Could not setup file logging: {e}")

        # Set logger level
        self.logger.setLevel(log_level)

        # Prevent duplicate messages from libraries (configurable via env vars)
        urllib3_level = getattr(logging, os.getenv('LOG_LEVEL_URLLIB3', 'WARNING').upper(), logging.WARNING)
        requests_level = getattr(logging, os.getenv('LOG_LEVEL_REQUESTS', 'WARNING').upper(), logging.WARNING)
        boto3_level = getattr(logging, os.getenv('LOG_LEVEL_BOTO3', 'WARNING').upper(), logging.WARNING)
        botocore_level = getattr(logging, os.getenv('LOG_LEVEL_BOTOCORE', 'WARNING').upper(), logging.WARNING)
        
        logging.getLogger('urllib3').setLevel(urllib3_level)
        logging.getLogger('requests').setLevel(requests_level)
        logging.getLogger('boto3').setLevel(boto3_level)
        logging.getLogger('botocore').setLevel(botocore_level)

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger with the specified name"""
        return logging.getLogger(f'comfyui-serverless.{name}')

    def debug(self, message: str, *args, **kwargs):
        """Log debug message"""
        self.logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        """Log info message"""
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        """Log warning message"""
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        """Log error message"""
        self.logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        """Log critical message"""
        self.logger.critical(message, *args, **kwargs)


# Global logger instance
logger = ComfyUILogger()


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the specified module"""
    return logger.get_logger(name)


def setup_logging():
    """Initialize logging (called once at application startup)"""
    # This function exists to ensure logging is properly initialized
    # The actual setup happens in the ComfyUILogger constructor
    pass
