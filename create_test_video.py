#!/usr/bin/env python3
"""
Create a simple test video for SmolVLM2 video inference testing
"""

import cv2
import numpy as np
import os

def create_test_video(output_path="/Users/jackmodesett/SmolVLM2/test_video.mp4"):
    """Create a simple test video with moving shapes."""
    
    # Video parameters
    width, height = 640, 480
    fps = 30
    duration = 3  # seconds
    total_frames = fps * duration
    
    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    print(f"🎬 Creating test video: {output_path}")
    
    for frame_num in range(total_frames):
        # Create a frame
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Background color changes over time
        bg_color = int(50 + 50 * np.sin(frame_num * 0.1))
        frame[:, :] = (bg_color, bg_color // 2, bg_color // 3)
        
        # Moving circle
        circle_x = int(width * 0.2 + (width * 0.6) * (frame_num / total_frames))
        circle_y = int(height * 0.5 + 50 * np.sin(frame_num * 0.2))
        cv2.circle(frame, (circle_x, circle_y), 30, (0, 255, 0), -1)
        
        # Moving rectangle
        rect_x = int(width * 0.8 - (width * 0.6) * (frame_num / total_frames))
        rect_y = int(height * 0.3 + 30 * np.cos(frame_num * 0.15))
        cv2.rectangle(frame, (rect_x - 20, rect_y - 15), (rect_x + 20, rect_y + 15), (255, 0, 0), -1)
        
        # Add text showing frame number
        text = f"Frame {frame_num + 1}/{total_frames}"
        cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Add text showing action
        if frame_num < total_frames // 3:
            action_text = "Green circle moves right"
        elif frame_num < 2 * total_frames // 3:
            action_text = "Both shapes moving"
        else:
            action_text = "Red rectangle moves left"
        
        cv2.putText(frame, action_text, (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        out.write(frame)
    
    out.release()
    print(f"✅ Test video created successfully!")
    print(f"📁 Location: {output_path}")
    print(f"📊 Details: {width}x{height}, {fps} FPS, {duration} seconds")
    
    return output_path

if __name__ == "__main__":
    create_test_video()