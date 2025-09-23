#!/usr/bin/env python3
"""
SmolVLM2 Video Analysis API for Railway Deployment
FastAPI wrapper for the video highlight and workout analysis system
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
import json
import traceback
from pathlib import Path
import uvicorn

# Import Railway-compatible video analysis system
from railway_video_generator import RailwayVideoGenerator

app = FastAPI(
    title="SmolVLM2 Video Analysis API",
    description="AI-powered video analysis for highlights and workout timestamps",
    version="1.0.0"
)

# Add CORS middleware for web app integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global generator instance
generator = None

@app.on_event("startup")
async def startup_event():
    """Initialize the video analysis system on startup."""
    global generator
    try:
        # Use transformers for Railway deployment (no MLX on Linux)
        generator = RailwayVideoGenerator(
            model_name="HuggingFaceTB/SmolVLM2-500M-Video-Instruct"
        )
        print("✅ SmolVLM2 Video Analysis API initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize video analysis system: {e}")
        # Don't fail startup, just log the error

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
            "health": "/health"
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
        results = generator.generate_highlights(
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
