#!/usr/bin/env python3
"""
SmolVLM2 Video Analysis API - Railway Deployment
Handles video uploads and analysis using HuggingFace transformers directly.
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
import time
import shutil
import traceback
import uvicorn
from railway_video_generator import RailwayVideoGenerator
from async_api import router as async_router, init_async_api
from session_manager import SessionManager
from task_manager import BackgroundTaskManager as TaskManager

app = FastAPI(
    title="SmolVLM2 Video Analysis API",
    description="Video analysis using SmolVLM2 for highlights and workout analysis",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Global instances
generator = None
session_manager = None
task_manager = None

@app.on_event("startup")
async def startup_event():
    """Initialize the video analysis system on startup."""
    global generator, session_manager, task_manager
    try:
        # Initialize video generator
        generator = RailwayVideoGenerator(
            model_name="HuggingFaceTB/SmolVLM2-500M-Video-Instruct"
        )
        
        # Initialize session and task managers
        session_manager = SessionManager()
        task_manager = TaskManager()
        
        # Initialize async API with managers
        init_async_api(session_manager, task_manager, generator)
        
        print("✅ SmolVLM2 Video Analysis API initialized successfully")
        print("✅ Session management enabled")
        print("✅ Async processing enabled")
        
    except Exception as e:
        print(f"❌ Failed to initialize video analysis system: {e}")
        # Don't fail startup, just log the error

# Include async API routes
app.include_router(async_router)

@app.on_event("shutdown") 
async def shutdown_event():
    """Cleanup on shutdown."""
    global generator
    if generator:
        generator.cleanup()

@app.get("/")
async def root():
    """Health check and API info."""
    return {
        "message": "SmolVLM2 Video Analysis API",
        "status": "healthy",
        "version": "1.0.0",
        "endpoints": {
            "analyze_highlights": "/analyze/highlights",
            "analyze_workout": "/analyze/workout", 
            "health": "/health",
            "async_api": "/api/v1/video/*"
        }
    }

@app.get("/health")
async def health_check():
    """Detailed health check."""
    global generator
    return {
        "status": "healthy",
        "analyzer_initialized": generator is not None,
        "ready": True
    }

@app.post("/analyze/highlights")
async def analyze_highlights(
    video: UploadFile = File(...),
    min_significance: int = Form(default=6),
    max_highlights: int = Form(default=10)
):
    """
    Analyze video for highlights and significant moments.
    
    Args:
        video: Video file to analyze
        min_significance: Minimum significance score (1-10)
        max_highlights: Maximum number of highlights to return
    
    Returns:
        JSON with highlighted moments and timestamps
    """
    global generator
    
    if not generator:
        raise HTTPException(status_code=503, detail="Video analysis system not initialized")
    
    # Save uploaded video to temporary file
    temp_dir = tempfile.mkdtemp()
    video_path = os.path.join(temp_dir, f"video_{video.filename}")
    
    try:
        # Save uploaded file
        with open(video_path, "wb") as f:
            content = await video.read()
            f.write(content)
        
        # Analyze video for highlights
        results = generator.generate_highlights_with_progress(
            video_path=video_path,
            min_significance=min_significance,
            max_highlights=max_highlights
        )
        
        # Clean up paths in response (don't expose server paths)
        clean_results = clean_file_paths(results)
        
        return JSONResponse(content={
            "success": True,
            "analysis_type": "highlights",
            "data": clean_results
        })
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Video analysis failed: {str(e)}"
        )
    
    finally:
        # Cleanup temporary files
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
            os.rmdir(temp_dir)
        except:
            pass

@app.post("/analyze/workout")  
async def analyze_workout(
    video: UploadFile = File(...),
    segment_duration: int = Form(default=15),
    system_prompt: str = Form(default="Analyze this workout video and identify exercise transitions with timestamps"),
    user_prompt: str = Form(default="Break this workout into exercise steps with timestamps")
):
    """
    Analyze workout video for exercise timestamps and transitions.
    
    Args:
        video: Workout video file to analyze
        segment_duration: Duration of analysis segments in seconds
        system_prompt: Custom system prompt for analysis
        user_prompt: Custom user prompt for specific requirements
    
    Returns:
        JSON with exercise steps and precise timestamps
    """
    global generator
    
    if not generator:
        raise HTTPException(status_code=503, detail="Video analysis system not initialized")
    
    # Save uploaded video to temporary file
    temp_dir = tempfile.mkdtemp()
    video_path = os.path.join(temp_dir, f"workout_{video.filename}")
    
    try:
        # Save uploaded file
        with open(video_path, "wb") as f:
            content = await video.read()
            f.write(content)
        
        # Analyze workout video with timestamps
        results = generator.analyze_workout_with_timestamps(
            video_path=video_path,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            segment_duration=segment_duration
        )
        
        # Clean up paths in response
        clean_results = clean_file_paths(results)
        
        return JSONResponse(content={
            "success": True,
            "analysis_type": "workout_timestamps", 
            "data": clean_results
        })
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Workout analysis failed: {str(e)}"
        )
    
    finally:
        # Cleanup temporary files
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
            os.rmdir(temp_dir)
        except:
            pass

def clean_file_paths(data):
    """Remove server file paths from response data for security."""
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            if key in ['video_path', 'segment_path'] and isinstance(value, str):
                # Just keep filename, remove full path
                cleaned[key] = os.path.basename(value)
            else:
                cleaned[key] = clean_file_paths(value)
        return cleaned
    elif isinstance(data, list):
        return [clean_file_paths(item) for item in data]
    else:
        return data

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
