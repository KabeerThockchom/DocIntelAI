import logging
import time
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("document_processor")

def log_step(component: str, message: str, level: str = "info"):
    """
    Log a step in the processing pipeline.
    
    Args:
        component: Component name (e.g., 'RAG', 'Embedding', etc.)
        message: Log message
        level: Log level (info, warning, error)
    """
    if level == "warning":
        logger.warning(f"[{component}] {message}")
    elif level == "error":
        logger.error(f"[{component}] {message}")
    else:
        logger.info(f"[{component}] {message}")

class Timer:
    """
    Context manager for timing operations with streaming updates.
    """
    def __init__(self, operation: str, update_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None):
        """
        Initialize the timer.
        
        Args:
            operation: Operation name to time
            update_callback: Optional callback function to send streaming updates
                             Function signature: callback(stage, details)
        """
        self.operation = operation
        self.start_time = None
        self.update_callback = update_callback
        
    def __enter__(self):
        """Start the timer and log the operation start."""
        self.start_time = time.time()
        log_step(self.operation, "Started")
        
        # Send real-time update if callback is provided
        if self.update_callback:
            try:
                self.update_callback(f"{self.operation.lower()}_started", {
                    "operation": self.operation,
                    "status": "started",
                    "timestamp": time.time()
                })
                
                # Start a background thread to send periodic updates for long-running operations
                if "retrieve_chunks" in self.operation.lower() or "generate_answer" in self.operation.lower():
                    import threading
                    
                    def send_periodic_updates():
                        # Only send updates while the operation is still running
                        while hasattr(self, 'start_time') and self.start_time is not None:
                            elapsed = time.time() - self.start_time
                            # After 1 second, start sending progress updates
                            if elapsed > 1.0:
                                try:
                                    self.update_callback(f"{self.operation.lower()}_progress", {
                                        "operation": self.operation,
                                        "status": "in_progress",
                                        "elapsed": elapsed,
                                        "timestamp": time.time()
                                    })
                                except Exception as e:
                                    pass  # Silently ignore errors in background thread
                            
                            # Sleep for a short time before checking again
                            time.sleep(0.1)
                    
                    # Start the background thread
                    threading.Thread(target=send_periodic_updates, daemon=True).start()
                
            except Exception as e:
                log_step(self.operation, f"Error sending start update: {str(e)}", level="warning")
            
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        End the timer and log the operation completion with duration.
        Also handles sending completion update via callback if provided.
        """
        if self.start_time:
            duration = time.time() - self.start_time
            
            # Log completion without any artificial delay
            log_step(self.operation, f"Completed in {duration:.2f} seconds")
            
            # Send real-time update if callback is provided
            if self.update_callback:
                try:
                    self.update_callback(f"{self.operation.lower()}_completed", {
                        "operation": self.operation,
                        "status": "completed",
                        "duration": duration,
                        "timestamp": time.time()
                    })
                    
                    # Set start_time to None to signal background threads to stop
                    self.start_time = None
                    
                except Exception as e:
                    log_step(self.operation, f"Error sending completion update: {str(e)}", level="warning")
                
    def send_progress_update(self, progress: float, details: Optional[Dict[str, Any]] = None):
        """
        Send a progress update during the timing operation.
        
        Args:
            progress: Progress value between 0.0 and 1.0
            details: Optional details to include in the update
        """
        if not self.update_callback:
            return
            
        update_details = {
            "operation": self.operation,
            "status": "in_progress",
            "progress": progress,
            "timestamp": time.time()
        }
        
        if details:
            update_details.update(details)
        
        try:
            self.update_callback(f"{self.operation.lower()}_progress", update_details)
        except Exception as e:
            log_step(self.operation, f"Error sending progress update: {str(e)}", level="warning")