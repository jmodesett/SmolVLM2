#!/usr/bin/env python3
"""
Session Manager for Async Video Processing
Manages video processing sessions with thread-safe operations.
"""

import uuid
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages video processing sessions with thread-safe operations.
    
    Sessions track the state of asynchronous video analysis including:
    - Current status (queued, processing, completed, failed, cancelled)
    - Progress percentage (0-100)
    - Results when completed
    - Error messages if failed
    - Timestamps for creation and updates
    """
    
    def __init__(self):
        """Initialize the session manager with empty session storage."""
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        logger.info("SessionManager initialized")
    
    def create_session(
        self,
        video_path: str,
        analysis_type: str,
        params: Dict[str, Any]
    ) -> str:
        """
        Create a new video processing session.
        
        Args:
            video_path: Path to the uploaded video file
            analysis_type: Type of analysis ("highlights" or "workout")
            params: Additional parameters for the analysis
        
        Returns:
            str: Unique session ID (UUID)
        """
        session_id = str(uuid.uuid4())
        
        session_data = {
            "session_id": session_id,
            "status": "queued",
            "progress": 0,
            "message": "Video uploaded, queued for processing",
            "video_path": video_path,
            "analysis_type": analysis_type,
            "params": params,
            "result": None,
            "error": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "metadata": {}
        }
        
        with self._lock:
            self._sessions[session_id] = session_data
            logger.info(f"Created session {session_id} for {analysis_type} analysis")
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data by ID.
        
        Args:
            session_id: The session ID to lookup
        
        Returns:
            dict: Session data if found, None otherwise
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                # Return a copy to prevent external modifications
                return session.copy()
            return None
    
    def update_session(self, session_id: str, **updates) -> bool:
        """
        Update session with new data.
        
        Args:
            session_id: The session ID to update
            **updates: Key-value pairs to update in the session
        
        Returns:
            bool: True if updated successfully, False if session not found
        """
        with self._lock:
            if session_id not in self._sessions:
                logger.warning(f"Attempted to update non-existent session: {session_id}")
                return False
            
            # Update the session
            self._sessions[session_id].update(updates)
            self._sessions[session_id]["updated_at"] = datetime.now()
            
            # Log significant status changes
            if "status" in updates:
                logger.info(
                    f"Session {session_id} status changed to: {updates['status']}"
                )
            
            return True
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and its data.
        
        Args:
            session_id: The session ID to delete
        
        Returns:
            bool: True if deleted, False if session not found
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info(f"Deleted session {session_id}")
                return True
            logger.warning(f"Attempted to delete non-existent session: {session_id}")
            return False
    
    def list_sessions(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None
    ) -> list:
        """
        List all sessions, optionally filtered by status.
        
        Args:
            status: Filter by status (queued, processing, completed, failed, cancelled)
            limit: Maximum number of sessions to return
        
        Returns:
            list: List of session data dictionaries
        """
        with self._lock:
            sessions = list(self._sessions.values())
            
            # Filter by status if provided
            if status:
                sessions = [s for s in sessions if s["status"] == status]
            
            # Sort by creation time (newest first)
            sessions.sort(key=lambda x: x["created_at"], reverse=True)
            
            # Apply limit if provided
            if limit:
                sessions = sessions[:limit]
            
            return [s.copy() for s in sessions]
    
    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """
        Remove sessions older than max_age_hours.
        
        Args:
            max_age_hours: Maximum age of sessions to keep (default: 24 hours)
        
        Returns:
            int: Number of sessions deleted
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        deleted_count = 0
        
        with self._lock:
            # Find expired sessions
            expired_sessions = [
                sid for sid, session in self._sessions.items()
                if session["created_at"] < cutoff_time
            ]
            
            # Delete expired sessions
            for session_id in expired_sessions:
                del self._sessions[session_id]
                deleted_count += 1
            
            if deleted_count > 0:
                logger.info(
                    f"Cleaned up {deleted_count} expired sessions "
                    f"(older than {max_age_hours} hours)"
                )
        
        return deleted_count
    
    def get_session_count(self, status: Optional[str] = None) -> int:
        """
        Get count of sessions, optionally filtered by status.
        
        Args:
            status: Filter by status (queued, processing, completed, failed, cancelled)
        
        Returns:
            int: Number of sessions matching the criteria
        """
        with self._lock:
            if status:
                return sum(
                    1 for s in self._sessions.values()
                    if s["status"] == status
                )
            return len(self._sessions)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get overall session statistics.
        
        Returns:
            dict: Statistics including counts by status and total sessions
        """
        with self._lock:
            stats = {
                "total": len(self._sessions),
                "by_status": {},
                "oldest_session": None,
                "newest_session": None
            }
            
            # Count by status
            for session in self._sessions.values():
                status = session["status"]
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            # Find oldest and newest
            if self._sessions:
                sessions_list = list(self._sessions.values())
                sessions_list.sort(key=lambda x: x["created_at"])
                stats["oldest_session"] = sessions_list[0]["created_at"]
                stats["newest_session"] = sessions_list[-1]["created_at"]
            
            return stats
