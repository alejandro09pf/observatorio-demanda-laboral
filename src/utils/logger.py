import logging
from typing import Optional
from config.settings import get_settings

def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """Get a configured logger instance."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # Configure logger if not already configured
        level = level or get_settings().log_level
        logger.setLevel(getattr(logging, level.upper()))
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        # Add handler
        logger.addHandler(console_handler)
    
    return logger 