import time
from typing import Callable, Dict, Any, Optional

class Timer:
    """Context manager for timing operations and reporting progress."""
    
    def __init__(self, operation_name: str, callback: Optional[Callable] = None):
        """
        Initialize a timer with an operation name.
        
        Args:
            operation_name: Name of the operation being timed
            callback: Optional callback function to report progress
        """
        self.operation_name = operation_name
        self.callback = callback
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        """Start the timer and report operation started."""
        self.start_time = time.time()
        
        # Report start of operation
        if self.callback:
            self.callback(f"{self.operation_name.lower()}_started", {
                "operation": self.operation_name,
                "status": "started",
                "progress": 0.0
            })
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End the timer and report operation completed."""
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        # Report completion of operation
        if self.callback:
            self.callback(f"{self.operation_name.lower()}_completed", {
                "operation": self.operation_name,
                "status": "completed",
                "progress": 1.0,
                "duration": duration,
                "is_completed": True  # Explicitly mark as completed
            })
    
    def update_progress(self, progress: float, status: str = "in progress", details: Dict[str, Any] = None):
        """
        Update the progress of the operation.
        
        Args:
            progress: Progress value between 0 and 1
            status: Status message
            details: Additional details to include in the update
        """
        if progress < 0:
            progress = 0
        elif progress > 1:
            progress = 1
            
        if self.callback:
            update_details = {
                "operation": self.operation_name,
                "status": status,
                "progress": progress
            }
            
            # Include additional details if provided
            if details:
                update_details.update(details)
            
            # Set is_completed flag if progress is complete
            if progress >= 0.99:
                update_details["is_completed"] = True
                
            self.callback(f"{self.operation_name.lower()}_update", update_details) 