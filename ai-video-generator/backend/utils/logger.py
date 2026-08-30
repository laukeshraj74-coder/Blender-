"""
Simple logging utility for AI Video Generator backend.
Provides timestamped, component-based logging.
"""

import logging
import os
from pathlib import Path
from datetime import datetime

class AppLogger:
    """Application logger with file and console output."""
    
    def __init__(self, log_path=None):
        """Initialize logger."""
        if log_path is None:
            app_data = Path(os.environ.get('APPDATA', Path.home() / '.local' / 'share'))
            app_dir = app_data / 'AIVideoGenerator' / 'logs'
            app_dir.mkdir(parents=True, exist_ok=True)
            log_file = app_dir / f'app_{datetime.now().strftime("%Y%m%d")}.log'
            self.log_path = str(log_file)
        else:
            self.log_path = log_path
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='[%(levelname)s] %(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(self.log_path, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('AIVideoGenerator')
    
    def info(self, message, component='App'):
        """Log info message."""
        self.logger.info(f"[{component}] {message}")
    
    def warning(self, message, component='App'):
        """Log warning message."""
        self.logger.warning(f"[{component}] {message}")
    
    def error(self, message, component='App'):
        """Log error message."""
        self.logger.error(f"[{component}] {message}")
    
    def debug(self, message, component='App'):
        """Log debug message."""
        self.logger.debug(f"[{component}] {message}")


# Global logger instance
_logger_instance = None

def get_logger():
    """Get or create global logger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = AppLogger()
    return _logger_instance
