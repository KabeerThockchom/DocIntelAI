import logging
import time
from typing import Optional

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger("document_processor")

def log_step(step_name: str, message: str, level: str = "info"):
    """
    Log a step in the document processing pipeline.
    
    Args:
        step_name: Name of the processing step
        message: Log message
        level: Log level (info, warning, error, debug)
    """
    if level == "info":
        logger.info(f"[{step_name}] {message}")
    elif level == "warning":
        logger.warning(f"[{step_name}] {message}")
    elif level == "error":
        logger.error(f"[{step_name}] {message}")
    elif level == "debug":
        logger.debug(f"[{step_name}] {message}")

class Timer:
    """Simple timer for performance logging."""
    
    def __init__(self, step_name: str):
        self.step_name = step_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        log_step(self.step_name, f"Completed in {duration:.2f} seconds")