#!/usr/bin/env python3
"""
Background Task Manager for Async Video Processing
Executes video analysis tasks in background threads with cancellation support.
"""

import threading
import logging
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Callable, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """
    Manages background video processing tasks with a thread pool.
    
    Features:
    - Thread pool for concurrent task execution
    - Task cancellation support
    - Session-based task tracking
    - Comprehensive error handling
    - Task status monitoring
    
    Example:
        task_manager = BackgroundTaskManager(max_workers=4)
        
        # Submit a task
        future = task_manager.submit_task(
            session_id="session_123",
            analysis_fn=generator.generate_highlights,
            video_path="/path/to/video.mp4"
        )
        
        # Check status
        status = task_manager.get_task_status("session_123")
        
        # Cancel if needed
        task_manager.cancel_task("session_123")
    """
    
    def __init__(self, max_workers: int = 4):
        """
        Initialize the task manager.
        
        Args:
            max_workers: Maximum number of concurrent worker threads
        """
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: Dict[str, Future] = {}  # session_id -> Future
        self._task_info: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        logger.info(f"TaskManager initialized with {max_workers} workers")
    
    def submit_task(
        self,
        session_id: str,
        analysis_fn: Callable,
        *args,
        **kwargs
    ) -> Future:
        """
        Submit a video analysis task for background execution.
        
        Args:
            session_id: Session ID to associate with this task
            analysis_fn: Function to execute (e.g., generator.generate_highlights)
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
        
        Returns:
            Future: Future object representing the task
        """
        with self._lock:
            # Cancel existing task for this session if any
            if session_id in self._tasks:
                logger.warning(
                    f"Session {session_id} already has a task, cancelling old task"
                )
                self.cancel_task(session_id)
            
            # Submit the task
            future = self._executor.submit(
                self._execute_with_error_handling,
                session_id,
                analysis_fn,
                *args,
                **kwargs
            )
            
            # Track the task
            self._tasks[session_id] = future
            self._task_info[session_id] = {
                "started_at": datetime.now(),
                "status": "running",
                "error": None
            }
            
            # Add callback to clean up on completion
            future.add_done_callback(
                lambda f: self._task_done_callback(session_id, f)
            )
            
            logger.info(f"Submitted task for session {session_id}")
            return future
    
    def _execute_with_error_handling(
        self,
        session_id: str,
        analysis_fn: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute analysis function with proper error handling.
        
        Args:
            session_id: Session ID for logging
            analysis_fn: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Any: Result from the analysis function
        """
        try:
            logger.info(f"Starting task execution for session {session_id}")
            result = analysis_fn(*args, **kwargs)
            logger.info(f"Task completed successfully for session {session_id}")
            return result
        except Exception as e:
            logger.error(
                f"Task failed for session {session_id}: {str(e)}",
                exc_info=True
            )
            with self._lock:
                if session_id in self._task_info:
                    self._task_info[session_id]["error"] = str(e)
                    self._task_info[session_id]["status"] = "failed"
            raise
    
    def _task_done_callback(self, session_id: str, future: Future):
        """
        Callback executed when a task completes (success or failure).
        
        Args:
            session_id: Session ID of the completed task
            future: The completed Future object
        """
        with self._lock:
            if session_id in self._task_info:
                if future.cancelled():
                    self._task_info[session_id]["status"] = "cancelled"
                    logger.info(f"Task cancelled for session {session_id}")
                elif future.exception():
                    self._task_info[session_id]["status"] = "failed"
                    self._task_info[session_id]["error"] = str(future.exception())
                    logger.error(
                        f"Task failed for session {session_id}: "
                        f"{future.exception()}"
                    )
                else:
                    self._task_info[session_id]["status"] = "completed"
                    logger.info(f"Task completed for session {session_id}")
                
                self._task_info[session_id]["completed_at"] = datetime.now()
    
    def cancel_task(self, session_id: str) -> bool:
        """
        Cancel a running task.
        
        Args:
            session_id: Session ID of the task to cancel
        
        Returns:
            bool: True if cancelled, False if task not found or already done
        """
        with self._lock:
            if session_id not in self._tasks:
                logger.warning(
                    f"Attempted to cancel non-existent task: {session_id}"
                )
                return False
            
            future = self._tasks[session_id]
            
            # Try to cancel the future
            cancelled = future.cancel()
            
            if cancelled:
                logger.info(f"Successfully cancelled task for session {session_id}")
                self._task_info[session_id]["status"] = "cancelled"
            else:
                # Task already running or completed, can't cancel
                logger.info(
                    f"Could not cancel task for session {session_id} "
                    "(already running or completed)"
                )
            
            return cancelled
    
    def get_task_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a task.
        
        Args:
            session_id: Session ID to check
        
        Returns:
            dict: Task status information, None if task not found
        """
        with self._lock:
            if session_id not in self._task_info:
                return None
            
            info = self._task_info[session_id].copy()
            
            # Add additional info if task exists
            if session_id in self._tasks:
                future = self._tasks[session_id]
                info["is_running"] = future.running()
                info["is_done"] = future.done()
                info["is_cancelled"] = future.cancelled()
            
            return info
    
    def get_active_task_count(self) -> int:
        """
        Get the number of currently running tasks.
        
        Returns:
            int: Number of active tasks
        """
        with self._lock:
            return sum(
                1 for future in self._tasks.values()
                if future.running()
            )
    
    def cleanup_completed_tasks(self) -> int:
        """
        Remove completed tasks from tracking.
        
        Returns:
            int: Number of tasks cleaned up
        """
        with self._lock:
            completed_sessions = [
                sid for sid, future in self._tasks.items()
                if future.done()
            ]
            
            for session_id in completed_sessions:
                del self._tasks[session_id]
                # Keep task_info for history, but could also delete if needed
            
            if completed_sessions:
                logger.info(f"Cleaned up {len(completed_sessions)} completed tasks")
            
            return len(completed_sessions)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get overall task statistics.
        
        Returns:
            dict: Statistics about tasks
        """
        with self._lock:
            stats = {
                "max_workers": self.max_workers,
                "total_tasks": len(self._task_info),
                "active_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "cancelled_tasks": 0
            }
            
            # Count by status
            for info in self._task_info.values():
                status = info.get("status", "unknown")
                if status == "running":
                    stats["active_tasks"] += 1
                elif status == "completed":
                    stats["completed_tasks"] += 1
                elif status == "failed":
                    stats["failed_tasks"] += 1
                elif status == "cancelled":
                    stats["cancelled_tasks"] += 1
            
            return stats
    
    def shutdown(self, wait: bool = True):
        """
        Shutdown the task manager and stop accepting new tasks.
        
        Args:
            wait: If True, wait for all tasks to complete before shutting down
        """
        logger.info(f"Shutting down TaskManager (wait={wait})")
        self._executor.shutdown(wait=wait)
    
    # Compatibility methods for async API
    def create_task(self, task_id: str, session_id: str, task_type: str, parameters: Dict[str, Any]):
        """
        Compatibility method for async API - maps task_id to session_id.
        
        Args:
            task_id: Unique task identifier
            session_id: Session identifier
            task_type: Type of task (highlights, workout)
            parameters: Task parameters
        """
        with self._lock:
            # Store task mapping
            if not hasattr(self, '_task_mappings'):
                self._task_mappings = {}
            
            self._task_mappings[task_id] = session_id
            
            # Initialize task info with async API compatible structure
            self._task_info[task_id] = {
                "task_id": task_id,
                "session_id": session_id,
                "task_type": task_type,
                "parameters": parameters,
                "status": "created",
                "current_step": "Task created",
                "progress": 0,
                "segments_completed": 0,
                "total_segments": 0,
                "started_at": datetime.now(),
                "error": None
            }
            
            logger.info(f"Created task {task_id} for session {session_id}")
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task information by task ID (compatibility method).
        
        Args:
            task_id: Task identifier
            
        Returns:
            dict: Task information or None if not found
        """
        with self._lock:
            return self._task_info.get(task_id)
    
    def update_task(self, task_id: str, updates: Dict[str, Any]):
        """
        Update task information (compatibility method).
        
        Args:
            task_id: Task identifier
            updates: Dictionary of fields to update
        """
        with self._lock:
            if task_id in self._task_info:
                self._task_info[task_id].update(updates)
                self._task_info[task_id]["updated_at"] = datetime.now()
                
                logger.debug(f"Updated task {task_id}: {updates}")
            else:
                logger.warning(f"Attempted to update non-existent task: {task_id}")