#!/usr/bin/env python3
"""
Railway-Compatible Video Highlight Generator
Uses transformers directly instead of MLX for Linux deployment
"""

import torch
from transformers import AutoProcessor, AutoModelForImageTextToText
import tempfile
import os
import cv2
import json
from typing import List, Dict
import time

class RailwayVideoGenerator:
    """Railway-compatible video analysis using transformers directly."""
    
    def __init__(self, model_name="HuggingFaceTB/SmolVLM2-500M-Video-Instruct"):
        self.model_name = model_name
        self.temp_dir = tempfile.mkdtemp(prefix="smolvlm_railway_")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🎬 Railway SmolVLM2 Video Generator")
        print(f"📁 Temporary files: {self.temp_dir}")
        print(f"🖥️  Using device: {self.device}")
        
        # Load model and processor
        try:
            self.processor = AutoProcessor.from_pretrained(model_name)
            self.model = AutoModelForImageTextToText.from_pretrained(
                model_name,
                torch_dtype=torch.float32,
                device_map=None,
            ).to(self.device)
            print("✅ Model loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            raise
    
    def analyze_video_transformers(self, video_path: str, system_prompt: str, user_prompt: str) -> Dict:
        """Analyze video using transformers directly."""
        try:
            # Prepare conversation
            messages = [
                {
                    "role": "system", 
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "video", "path": video_path},
                        {"type": "text", "text": user_prompt}
                    ]
                },
            ]
            
            # Process with transformers
            inputs = self.processor.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
            )
            
            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate response
            with torch.no_grad():
                generated_ids = self.model.generate(**inputs, max_new_tokens=200)
            
            generated_texts = self.processor.batch_decode(
                generated_ids,
                skip_special_tokens=True,
            )
            
            response = generated_texts[0]
            
            return {
                'response': response,
                'analysis_success': True
            }
            
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            return {
                'response': f"Analysis failed: {e}",
                'analysis_success': False
            }
    
    def extract_video_segments(self, video_path: str, segment_duration: int = 30) -> List[str]:
        """Extract video segments (simplified for Railway)."""
        print(f"✂️  Extracting segments from video: {video_path}")
        
        # Get video info
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        total_duration = total_frames / fps
        cap.release()
        
        segments = []
        start_time = 0
        segment_count = 0
        
        # For Railway, just extract a few key segments to avoid timeout
        max_segments = 3  # Limit for Railway deployment
        segment_interval = total_duration / max_segments
        
        for i in range(max_segments):
            start_time = i * segment_interval
            end_time = min(start_time + segment_duration, total_duration)
            
            segment_filename = f"railway_segment_{segment_count:03d}_{start_time:.1f}-{end_time:.1f}s.mp4"
            segment_path = os.path.join(self.temp_dir, segment_filename)
            
            # Extract using ffmpeg
            cmd = [
                'ffmpeg', '-y', '-loglevel', 'quiet',
                '-i', video_path,
                '-ss', str(start_time),
                '-t', str(end_time - start_time),
                '-c', 'copy',
                segment_path
            ]
            
            try:
                import subprocess
                subprocess.run(cmd, check=True)
                segments.append(segment_path)
                segment_count += 1
            except subprocess.CalledProcessError:
                print(f"⚠️  Failed to extract segment {segment_count}")
                continue
        
        print(f"📦 Extracted {len(segments)} segments for Railway")
        return segments
    
    def generate_highlights(self, video_path: str, output_file: str = None) -> Dict:
        """Generate video highlights (Railway-compatible)."""
        start_time = time.time()
        
        print(f"🎯 Generating highlights for Railway deployment...")
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Extract segments
        segments = self.extract_video_segments(video_path)
        
        if not segments:
            return {"error": "No segments extracted", "highlights": []}
        
        # Analyze segments
        highlights = []
        system_prompt = "Analyze this video segment and identify significant events or highlights."
        
        for i, segment_path in enumerate(segments):
            print(f"📹 Analyzing segment {i+1}/{len(segments)}")
            
            analysis = self.analyze_video_transformers(
                segment_path, 
                system_prompt,
                "What are the key highlights in this video segment?"
            )
            
            if analysis['analysis_success']:
                highlights.append({
                    'segment': i+1,
                    'description': analysis['response'],
                    'segment_path': os.path.basename(segment_path)
                })
        
        results = {
            'video_path': video_path,
            'processing_time_seconds': time.time() - start_time,
            'highlights_found': len(highlights),
            'highlights': highlights,
            'deployment': 'railway'
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
        
        return results
    
    def analyze_workout_with_timestamps(self, video_path: str, system_prompt: str = None, 
                                      user_prompt: str = None, segment_duration: int = 20,
                                      output_file: str = None) -> Dict:
        """Analyze workout video with timestamps (Railway-compatible)."""
        start_time = time.time()
        
        print(f"🏋️  Railway workout analysis: {video_path}")
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Default prompts for workout analysis
        if system_prompt is None:
            system_prompt = "Analyze this workout video and identify the exercises being performed."
        
        if user_prompt is None:
            user_prompt = "What exercises are being performed in this video? Provide timestamps."
        
        # Get video info
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        total_duration = total_frames / fps
        cap.release()
        
        # Extract fewer segments for Railway to avoid timeout
        segments = self.extract_video_segments(video_path, segment_duration)
        
        workout_analyses = []
        for i, segment_path in enumerate(segments):
            print(f"🏋️  Analyzing workout segment {i+1}/{len(segments)}")
            
            analysis = self.analyze_video_transformers(
                segment_path, 
                system_prompt,
                user_prompt
            )
            
            # Add timestamp info
            segment_duration_calc = total_duration / len(segments)
            start_timestamp = i * segment_duration_calc
            end_timestamp = min(start_timestamp + segment_duration_calc, total_duration)
            
            analysis.update({
                'start_timestamp': start_timestamp,
                'end_timestamp': end_timestamp,
                'duration': end_timestamp - start_timestamp,
                'timestamp_formatted': f"{self._format_timestamp(start_timestamp)} - {self._format_timestamp(end_timestamp)}"
            })
            
            workout_analyses.append(analysis)
        
        # Create exercise steps
        exercise_steps = []
        for i, analysis in enumerate(workout_analyses):
            if analysis['analysis_success']:
                exercise_steps.append({
                    'exercise_name': f"Exercise {i+1}",
                    'start_timestamp': analysis['start_timestamp'],
                    'end_timestamp': analysis['end_timestamp'],
                    'duration': analysis['duration'],
                    'timestamp_formatted': analysis['timestamp_formatted'],
                    'description': analysis['response']
                })
        
        results = {
            'video_path': video_path,
            'analysis_type': 'workout_with_timestamps',
            'processing_time_seconds': time.time() - start_time,
            'total_duration_seconds': total_duration,
            'total_segments_analyzed': len(segments),
            'system_prompt': system_prompt,
            'user_prompt': user_prompt,
            'segment_analyses': workout_analyses,
            'exercise_steps': exercise_steps,
            'summary': {
                'total_exercises_identified': len(exercise_steps),
                'video_duration_formatted': self._format_timestamp(total_duration),
                'deployment': 'railway'
            }
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
        
        return results
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds as MM:SS timestamp."""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def cleanup(self):
        """Clean up temporary files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(f"🧹 Cleaned up temporary files")