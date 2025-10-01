#!/usr/bin/env python3
"""
Async API endpoints for SmolVLM2 Video Analysis
Provides session-based video processing with progress tracking
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import tempfile
import os
import asyncio
from typing import Optional, Dict, Any
import uuid
from session_manager import SessionManager
from task_manager import BackgroundTaskManager as TaskManager
from railway_video_generator import RailwayVideoGenerator

# Create router for async API endpoints
router = APIRouter(prefix="/api/v1/video", tags=["Async Video Analysis"])

# Global managers (will be initialized in app.py)
session_manager: Optional[SessionManager] = None
task_manager: Optional[TaskManager] = None
generator: Optional[RailwayVideoGenerator] = None

def init_async_api(sm: SessionManager, tm: TaskManager, gen: RailwayVideoGenerator):
    """Initialize the async API with manager instances."""
    global session_manager, task_manager, generator
    session_manager = sm
    task_manager = tm
    generator = gen

@router.post("/upload")
async def upload_video(
    video: UploadFile = File(...),
    description: str = Form(default="")
):
    """
    Upload a video and create a new session.
    
    Returns:
        session_id: Unique identifier for this video session
        video_info: Basic information about the uploaded video
    """
    if not session_manager or not generator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    # Create new session
    session_id = str(uuid.uuid4())
    
    # Save uploaded video
    temp_dir = tempfile.mkdtemp(prefix=f"session_{session_id}_")
    video_path = os.path.join(temp_dir, f"video_{video.filename}")
    
    try:
        # Save uploaded file
        with open(video_path, "wb") as f:
            content = await video.read()
            f.write(content)
        
        # Get video info
        import cv2
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        video_info = {
            "filename": video.filename,
            "duration": duration,
            "fps": fps,
            "resolution": f"{width}x{height}",
            "frames": total_frames
        }
        
        # Create session
        session_id = session_manager.create_session(
            video_path=video_path,
            analysis_type="upload",
            params={
                "video_info": video_info,
                "description": description,
                "filename": video.filename
            }
        )
        
        return {
            "session_id": session_id,
            "video_info": video_info,
            "status": "uploaded",
            "message": "Video uploaded successfully"
        }
        
    except Exception as e:
        # Cleanup on error
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/analyze/{session_id}")
async def start_analysis(
    session_id: str,
    analysis_type: str = Form(...),  # "highlights" or "workout"
    min_significance: int = Form(default=6),
    max_highlights: int = Form(default=10),
    segment_duration: int = Form(default=15),
    system_prompt: str = Form(default=""),
    user_prompt: str = Form(default="")
):
    """
    Start video analysis for a session.
    
    Args:
        session_id: Session identifier from upload
        analysis_type: "highlights" or "workout"
        min_significance: Minimum significance score (for highlights)
        max_highlights: Maximum highlights to return
        segment_duration: Duration of analysis segments
        system_prompt: Custom system prompt
        user_prompt: Custom user prompt
    """
    if not session_manager or not task_manager or not generator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    # Validate session
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["status"] != "queued":
        raise HTTPException(status_code=400, detail="Session not in uploadable state")
    
    # Validate analysis type
    if analysis_type not in ["highlights", "workout"]:
        raise HTTPException(status_code=400, detail="analysis_type must be 'highlights' or 'workout'")
    
    # Create task
    task_id = str(uuid.uuid4())
    
    # Prepare task parameters
    task_params = {
        "video_path": session["video_path"],
        "analysis_type": analysis_type,
        "min_significance": min_significance,
        "max_highlights": max_highlights,
        "segment_duration": segment_duration,
        "system_prompt": system_prompt or get_default_system_prompt(analysis_type),
        "user_prompt": user_prompt or get_default_user_prompt(analysis_type)
    }
    
    # Start analysis task
    task_manager.create_task(
        task_id=task_id,
        session_id=session_id,
        task_type=analysis_type,
        parameters=task_params
    )
    
    # Update session status
    session_manager.update_session(session_id, status="analyzing", task_id=task_id)
    
    # Start background analysis
    asyncio.create_task(run_analysis_task(task_id, task_params))
    
    return {
        "task_id": task_id,
        "session_id": session_id,
        "analysis_type": analysis_type,
        "status": "started",
        "message": "Analysis started successfully"
    }

@router.get("/progress/{session_id}")
async def get_progress(session_id: str):
    """
    Get analysis progress for a session.
    
    Returns:
        status: Current status (uploaded, analyzing, completed, failed)
        progress: Progress percentage (0-100)
        current_step: Description of current processing step
        results: Analysis results (if completed)
    """
    if not session_manager or not task_manager:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    # Get session
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    response = {
        "session_id": session_id,
        "status": session["status"],
        "video_info": session["params"].get("video_info", {})
    }
    
    # If analyzing, get task progress
    if session["status"] == "analyzing" and "task_id" in session:
        task = task_manager.get_task(session["task_id"])
        if task:
            response.update({
                "progress": task["progress"],
                "current_step": task["current_step"],
                "segments_completed": task.get("segments_completed", 0),
                "total_segments": task.get("total_segments", 0)
            })
    
    # If completed, include results
    elif session["status"] == "completed":
        if "results" in session:
            response["results"] = session["results"]
    
    # If failed, include error
    elif session["status"] == "failed":
        if "error" in session:
            response["error"] = session["error"]
    
    return response

@router.get("/results/{session_id}")
async def get_results(session_id: str):
    """
    Get final analysis results for a completed session.
    
    Returns:
        Full analysis results with highlights/workout data
    """
    if not session_manager:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["status"] != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Session not completed. Current status: {session['status']}"
        )
    
    if "results" not in session:
        raise HTTPException(status_code=500, detail="Results not found")
    
    return {
        "session_id": session_id,
        "video_info": session["params"].get("video_info", {}),
        "analysis_complete": True,
        "results": session["results"]
    }

@router.delete("/session/{session_id}")
async def cleanup_session(session_id: str):
    """
    Clean up a session and its associated files.
    
    Args:
        session_id: Session to clean up
    """
    if not session_manager or not task_manager:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Cancel any running tasks
        if "task_id" in session:
            task_manager.cancel_task(session["task_id"])
        
        # Clean up video files
        if "video_path" in session:
            video_dir = os.path.dirname(session["video_path"])
            if os.path.exists(video_dir):
                import shutil
                shutil.rmtree(video_dir)
        
        # Remove session
        session_manager.delete_session(session_id)
        
        return {
            "session_id": session_id,
            "status": "cleaned_up",
            "message": "Session cleaned up successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

# Helper functions

async def run_analysis_task(task_id: str, params: Dict[str, Any]):
    """Run the analysis task in the background."""
    try:
        # Update task status
        task_manager.update_task(task_id, {
            "status": "running",
            "current_step": "Initializing analysis...",
            "progress": 0
        })
        
        # Get task and session info
        task = task_manager.get_task(task_id)
        session = session_manager.get_session(task["session_id"])
        
        # Progress callback function
        def progress_callback(step: str, progress: int, segments_completed: int = 0, total_segments: int = 0):
            task_manager.update_task(task_id, {
                "current_step": step,
                "progress": progress,
                "segments_completed": segments_completed,
                "total_segments": total_segments
            })
        
        # Run analysis based on type
        if params["analysis_type"] == "highlights":
            results = await run_highlights_analysis(params, progress_callback)
        elif params["analysis_type"] == "workout":
            results = await run_workout_analysis(params, progress_callback)
        else:
            raise ValueError(f"Unknown analysis type: {params['analysis_type']}")
        
        # Update task as completed
        task_manager.update_task(task_id, {
            "status": "completed",
            "current_step": "Analysis completed",
            "progress": 100,
            "results": results
        })
        
        # Update session
        session_manager.update_session(task["session_id"], status="completed", results=results)
        
    except Exception as e:
        # Handle task failure
        error_msg = f"Analysis failed: {str(e)}"
        
        task_manager.update_task(task_id, {
            "status": "failed",
            "current_step": "Analysis failed",
            "error": error_msg
        })
        
        task = task_manager.get_task(task_id)
        session_manager.update_session(task["session_id"], status="failed", error=error_msg)

async def run_highlights_analysis(params: Dict[str, Any], progress_callback):
    """Run highlights analysis with progress tracking."""
    progress_callback("Starting highlights analysis...", 10)
    
    # Use generator with progress callback
    results = generator.generate_highlights_with_progress(
        video_path=params["video_path"],
        min_significance=params["min_significance"],
        max_highlights=params["max_highlights"],
        progress_callback=progress_callback
    )
    
    return results

async def run_workout_analysis(params: Dict[str, Any], progress_callback):
    """Run workout analysis with progress tracking."""
    progress_callback("Starting workout analysis...", 10)
    
    # Use generator with progress callback
    results = generator.analyze_workout_with_timestamps_progress(
        video_path=params["video_path"],
        system_prompt=params["system_prompt"],
        user_prompt=params["user_prompt"],
        segment_duration=params["segment_duration"],
        progress_callback=progress_callback
    )
    
    return results

def get_default_system_prompt(analysis_type: str) -> str:
    """Get default system prompt for analysis type."""
    if analysis_type == "highlights":
        return (
            "Analyze this video segment and identify if it contains any "
            "significant events, actions, or highlights. Focus on: "
            "1. Important actions or movements "
            "2. Key objects or people appearing "
            "3. Scene changes or transitions "
            "4. Any dramatic or notable moments. "
            "Rate the significance from 1-10 and explain why."
        )
    elif analysis_type == "workout":
        return (
            "Splice the video into steps between the displayed exercise with a short summary "
            "of what the movement is. Analyze this workout video segment and identify: "
            "1. The specific exercise being performed "
            "2. The movement phase (setup, execution, rest) "
            "3. Any transitions between exercises "
            "4. Proper form observations "
            "5. Whether this appears to be the start, middle, or end of an exercise set."
        )
    else:
        return "Analyze this video segment and describe what you see."

def get_default_user_prompt(analysis_type: str) -> str:
    """Get default user prompt for analysis type."""
    if analysis_type == "highlights":
        return "What significant events or highlights do you see in this video segment?"
    elif analysis_type == "workout":
        return "This is a workout video. Please break it into exercise steps and identify the movement being performed."
    else:
        return "Describe what happens in this video."