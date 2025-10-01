#!/usr/bin/env python3
"""
Test script for the async video analysis API
"""

import requests
import time
import json
import os

# API base URL (adjust for your deployment)
BASE_URL = "http://localhost:8000"

def test_async_workflow():
    """Test the complete async workflow."""
    print("🧪 Testing Async Video Analysis API")
    print("=" * 50)
    
    # 1. Upload a video
    print("1. Uploading test video...")
    
    # Use the existing test video if available
    video_path = "/Users/jackmodesett/SmolVLM2/test_video.mp4"
    
    if not os.path.exists(video_path):
        print("❌ Test video not found. Please run create_test_video.py first")
        return
    
    with open(video_path, "rb") as f:
        files = {"video": f}
        data = {"description": "Test video for async API"}
        response = requests.post(f"{BASE_URL}/api/v1/video/upload", files=files, data=data)
    
    if response.status_code != 200:
        print(f"❌ Upload failed: {response.text}")
        return
    
    upload_result = response.json()
    session_id = upload_result["session_id"]
    print(f"✅ Upload successful. Session ID: {session_id}")
    
    # 2. Start analysis
    print("2. Starting highlights analysis...")
    
    analysis_data = {
        "analysis_type": "highlights",
        "min_significance": 4,  # Lower threshold for test video
        "max_highlights": 5
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/video/analyze/{session_id}", data=analysis_data)
    
    if response.status_code != 200:
        print(f"❌ Analysis start failed: {response.text}")
        return
    
    analysis_result = response.json()
    print(f"✅ Analysis started. Task ID: {analysis_result['task_id']}")
    
    # 3. Monitor progress
    print("3. Monitoring progress...")
    
    while True:
        response = requests.get(f"{BASE_URL}/api/v1/video/progress/{session_id}")
        
        if response.status_code != 200:
            print(f"❌ Progress check failed: {response.text}")
            return
        
        progress = response.json()
        status = progress["status"]
        
        if status == "analyzing":
            current_progress = progress.get("progress", 0)
            current_step = progress.get("current_step", "Processing...")
            print(f"   📊 Progress: {current_progress}% - {current_step}")
            
        elif status == "completed":
            print("✅ Analysis completed!")
            break
            
        elif status == "failed":
            error = progress.get("error", "Unknown error")
            print(f"❌ Analysis failed: {error}")
            return
        
        time.sleep(2)  # Check every 2 seconds
    
    # 4. Get results
    print("4. Retrieving results...")
    
    response = requests.get(f"{BASE_URL}/api/v1/video/results/{session_id}")
    
    if response.status_code != 200:
        print(f"❌ Results retrieval failed: {response.text}")
        return
    
    results = response.json()
    print("✅ Results retrieved successfully!")
    
    # Display results summary
    analysis_results = results["results"]
    print(f"\n📊 Analysis Summary:")
    print(f"   🎬 Video: {results['video_info']['filename']}")
    print(f"   ⏱️  Duration: {results['video_info']['duration']:.1f}s")
    print(f"   🌟 Highlights found: {analysis_results['highlights_found']}")
    
    if analysis_results['highlights']:
        print(f"\n🏆 Top Highlights:")
        for i, highlight in enumerate(analysis_results['highlights'][:3], 1):
            print(f"   {i}. Score: {highlight['significance_score']}/10")
            print(f"      {highlight['description'][:80]}...")
    
    # 5. Cleanup
    print("5. Cleaning up session...")
    
    response = requests.delete(f"{BASE_URL}/api/v1/video/session/{session_id}")
    
    if response.status_code == 200:
        print("✅ Session cleaned up successfully!")
    else:
        print(f"⚠️  Cleanup warning: {response.text}")
    
    print("\n🎉 Async API test completed successfully!")

def test_workout_analysis():
    """Test workout analysis workflow."""
    print("\n🏋️ Testing Workout Analysis API")
    print("=" * 50)
    
    video_path = "/Users/jackmodesett/SmolVLM2/test_video.mp4"
    
    if not os.path.exists(video_path):
        print("❌ Test video not found.")
        return
    
    # Upload video
    with open(video_path, "rb") as f:
        files = {"video": f}
        data = {"description": "Test workout video"}
        response = requests.post(f"{BASE_URL}/api/v1/video/upload", files=files, data=data)
    
    if response.status_code != 200:
        print(f"❌ Upload failed: {response.text}")
        return
    
    session_id = response.json()["session_id"]
    print(f"✅ Upload successful. Session ID: {session_id}")
    
    # Start workout analysis
    analysis_data = {
        "analysis_type": "workout",
        "segment_duration": 10
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/video/analyze/{session_id}", data=analysis_data)
    
    if response.status_code != 200:
        print(f"❌ Analysis start failed: {response.text}")
        return
    
    print("✅ Workout analysis started")
    
    # Monitor progress
    while True:
        response = requests.get(f"{BASE_URL}/api/v1/video/progress/{session_id}")
        progress = response.json()
        
        if progress["status"] == "completed":
            print("✅ Workout analysis completed!")
            break
        elif progress["status"] == "failed":
            print(f"❌ Analysis failed: {progress.get('error', 'Unknown error')}")
            return
        elif progress["status"] == "analyzing":
            current_progress = progress.get("progress", 0)
            print(f"📊 Progress: {current_progress}%")
        
        time.sleep(2)
    
    # Get workout results
    response = requests.get(f"{BASE_URL}/api/v1/video/results/{session_id}")
    results = response.json()
    
    exercise_steps = results["results"]["exercise_steps"]
    print(f"\n🏋️ Workout Summary:")
    print(f"   📊 Exercise steps identified: {len(exercise_steps)}")
    
    for i, step in enumerate(exercise_steps[:3], 1):
        print(f"   {i}. {step['timestamp_formatted']} - {step['description'][:60]}...")
    
    # Cleanup
    requests.delete(f"{BASE_URL}/api/v1/video/session/{session_id}")
    print("✅ Session cleaned up")

if __name__ == "__main__":
    test_async_workflow()
    test_workout_analysis()