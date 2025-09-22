#!/usr/bin/env python3
"""
SmolVLM2 Video Highlight Generator
Implementation inspired by the HuggingFace blog post mention of video highlight extraction.
This script processes long videos and identifies key moments/highlights.
"""

import subprocess
import sys
import os
import tempfile
import cv2
import json
from pathlib import Path
from typing import List, Dict, Tuple
import time

class SmolVLMHighlightGenerator:
    """
    Video highlight generator using SmolVLM2.
    
    Based on the HuggingFace blog post, this processes long-form videos
    and extracts significant moments using SmolVLM2's video understanding.
    """
    
    def __init__(self, model_name="mlx-community/SmolVLM2-500M-Video-Instruct-mlx"):
        self.model_name = model_name
        self.temp_dir = tempfile.mkdtemp(prefix="smolvlm_highlights_")
        print(f"🎬 SmolVLM2 Video Highlight Generator")
        print(f"📁 Temporary files: {self.temp_dir}")
    
    def extract_video_segments(self, video_path: str, segment_duration: int = 30, 
                             overlap: int = 5) -> List[str]:
        """
        Extract overlapping segments from a long video for analysis.
        
        Args:
            video_path: Path to the input video
            segment_duration: Duration of each segment in seconds
            overlap: Overlap between segments in seconds
        
        Returns:
            List of paths to extracted segments
        """
        print(f"✂️  Extracting segments from video: {video_path}")
        
        # Get video info
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        total_duration = total_frames / fps
        cap.release()
        
        print(f"📊 Video info: {total_duration:.1f}s, {fps:.1f} FPS")
        
        segments = []
        start_time = 0
        segment_count = 0
        
        while start_time < total_duration:
            end_time = min(start_time + segment_duration, total_duration)
            
            # Create segment filename
            segment_filename = f"segment_{segment_count:03d}_{start_time:.1f}-{end_time:.1f}s.mp4"
            segment_path = os.path.join(self.temp_dir, segment_filename)
            
            # Extract segment using ffmpeg
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-ss', str(start_time),
                '-t', str(end_time - start_time),
                '-c', 'copy',
                segment_path
            ]
            
            try:
                subprocess.run(cmd, capture_output=True, check=True)
                segments.append(segment_path)
                print(f"  ✅ Extracted: {segment_filename}")
            except subprocess.CalledProcessError as e:
                print(f"  ❌ Failed to extract segment: {e}")
                continue
            
            # Move to next segment with overlap
            start_time += segment_duration - overlap
            segment_count += 1
        
        print(f"📦 Extracted {len(segments)} segments")
        return segments
    
    def analyze_segment(self, segment_path: str, system_prompt: str = None) -> Dict:
        """
        Analyze a video segment using SmolVLM2.
        
        Args:
            segment_path: Path to the video segment
            system_prompt: Custom system prompt for analysis
        
        Returns:
            Dictionary with analysis results
        """
        if system_prompt is None:
            system_prompt = (
                "Analyze this video segment and identify if it contains any "
                "significant events, actions, or highlights. Focus on: "
                "1. Important actions or movements "
                "2. Key objects or people appearing "
                "3. Scene changes or transitions "
                "4. Any dramatic or notable moments. "
                "Rate the significance from 1-10 and explain why."
            )
        
        prompt = "What significant events or highlights do you see in this video segment?"
        
        # Run MLX-VLM analysis
        cmd = [
            sys.executable, "-m", "mlx_vlm.smolvlm_video_generate",
            "--model", self.model_name,
            "--system", system_prompt,
            "--prompt", prompt,
            "--video", segment_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Parse the output to extract the actual response
            output_lines = result.stdout.strip().split('\n')
            
            # Find the actual response (after the separator)
            response_started = False
            response_lines = []
            
            for line in output_lines:
                if line.strip().startswith('=========='):
                    if response_started:
                        break
                    response_started = True
                    continue
                
                if response_started and line.strip():
                    # Skip metadata lines
                    if not any(skip in line for skip in ['Files:', 'Prompt:', 'tokens-per-sec', 'Peak memory:']):
                        response_lines.append(line.strip())
            
            response = ' '.join(response_lines).strip()
            
            # Extract significance score if mentioned
            significance_score = self._extract_significance_score(response)
            
            return {
                'segment_path': segment_path,
                'response': response,
                'significance_score': significance_score,
                'analysis_success': True
            }
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Analysis failed for {segment_path}: {e}")
            return {
                'segment_path': segment_path,
                'response': f"Analysis failed: {e}",
                'significance_score': 0,
                'analysis_success': False
            }
    
    def _extract_significance_score(self, response: str) -> int:
        """Extract significance score from response text."""
        import re
        
        # Look for patterns like "8/10", "score: 7", "rating of 5", etc.
        patterns = [
            r'(\d+)/10',
            r'score:?\s*(\d+)',
            r'rating:?\s*of\s*(\d+)',
            r'significance:?\s*(\d+)',
            r'(\d+)\s*out\s*of\s*10'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response.lower())
            if match:
                return int(match.group(1))
        
        # If no explicit score, try to infer from keywords
        high_significance_words = ['significant', 'important', 'dramatic', 'key', 'major', 'critical']
        medium_significance_words = ['notable', 'interesting', 'relevant', 'some']
        low_significance_words = ['minimal', 'little', 'minor', 'basic', 'simple']
        
        response_lower = response.lower()
        
        if any(word in response_lower for word in high_significance_words):
            return 7
        elif any(word in response_lower for word in medium_significance_words):
            return 5
        elif any(word in response_lower for word in low_significance_words):
            return 3
        
        return 5  # Default middle score
    
    def generate_highlights(self, video_path: str, output_file: str = None, 
                          min_significance: int = 6, max_highlights: int = 10) -> Dict:
        """
        Generate highlights from a video.
        
        Args:
            video_path: Path to the input video
            output_file: Path to save results (JSON)
            min_significance: Minimum significance score for highlights
            max_highlights: Maximum number of highlights to extract
        
        Returns:
            Dictionary with highlight results
        """
        start_time = time.time()
        
        print(f"🎯 Generating highlights for: {video_path}")
        print(f"📏 Settings: min_significance={min_significance}, max_highlights={max_highlights}")
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Step 1: Extract segments
        segments = self.extract_video_segments(video_path)
        
        if not segments:
            raise RuntimeError("No segments extracted from video")
        
        # Step 2: Analyze each segment
        print(f"\n🔍 Analyzing {len(segments)} segments...")
        analyses = []
        
        for i, segment_path in enumerate(segments, 1):
            print(f"  📹 Analyzing segment {i}/{len(segments)}: {os.path.basename(segment_path)}")
            analysis = self.analyze_segment(segment_path)
            analyses.append(analysis)
            
            if analysis['analysis_success']:
                print(f"    ⭐ Significance: {analysis['significance_score']}/10")
                print(f"    💭 Response: {analysis['response'][:100]}...")
            
            time.sleep(1)  # Be nice to the system
        
        # Step 3: Filter and rank highlights
        highlights = [
            analysis for analysis in analyses 
            if analysis['analysis_success'] and analysis['significance_score'] >= min_significance
        ]
        
        # Sort by significance score (descending)
        highlights.sort(key=lambda x: x['significance_score'], reverse=True)
        
        # Limit to max_highlights
        highlights = highlights[:max_highlights]
        
        # Step 4: Prepare results
        processing_time = time.time() - start_time
        
        results = {
            'video_path': video_path,
            'processing_time_seconds': processing_time,
            'total_segments_analyzed': len(segments),
            'highlights_found': len(highlights),
            'settings': {
                'min_significance': min_significance,
                'max_highlights': max_highlights
            },
            'highlights': highlights,
            'all_analyses': analyses
        }
        
        # Step 5: Save results
        if output_file is None:
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            output_file = f"{video_name}_highlights.json"
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Step 6: Print summary
        print(f"\n🎉 Highlight Generation Complete!")
        print(f"⏱️  Processing time: {processing_time:.1f} seconds")
        print(f"📊 Analyzed {len(segments)} segments")
        print(f"🌟 Found {len(highlights)} highlights")
        print(f"💾 Results saved to: {output_file}")
        
        if highlights:
            print(f"\n🏆 Top Highlights:")
            for i, highlight in enumerate(highlights[:5], 1):
                segment_name = os.path.basename(highlight['segment_path'])
                print(f"  {i}. {segment_name} (Score: {highlight['significance_score']}/10)")
                print(f"     {highlight['response'][:80]}...")
        
        return results
    
    def analyze_workout_with_timestamps(self, video_path: str, system_prompt: str = None, 
                                      user_prompt: str = None, segment_duration: int = 20,
                                      output_file: str = None) -> Dict:
        """
        Analyze a workout video with timestamp extraction for exercise transitions.
        
        This method specifically analyzes workout videos to identify exercise steps
        with start and end timestamps. It uses smaller segments for more precise timing.
        
        Args:
            video_path: Path to the workout video
            system_prompt: Custom system prompt for workout analysis
            user_prompt: User prompt for specific workout analysis requirements
            segment_duration: Duration of each segment in seconds (smaller for precise timing)
            output_file: Path to save results (JSON)
        
        Returns:
            Dictionary with workout analysis results including timestamps
        """
        start_time = time.time()
        
        print(f"🏋️  Analyzing workout video with timestamps: {video_path}")
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Default prompts for workout analysis
        if system_prompt is None:
            system_prompt = (
                "Splice the video into steps between the displayed exercise with a short summary "
                "of what the movement is. Analyze this workout video segment and identify: "
                "1. The specific exercise being performed "
                "2. The movement phase (setup, execution, rest) "
                "3. Any transitions between exercises "
                "4. Proper form observations "
                "5. Whether this appears to be the start, middle, or end of an exercise set."
            )
        
        if user_prompt is None:
            user_prompt = "This is a workout video. Please break it into exercise steps and identify the movement being performed."
        
        # Get video info for timestamp calculation
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        total_duration = total_frames / fps
        cap.release()
        
        print(f"📊 Video info: {total_duration:.1f}s, {fps:.1f} FPS")
        
        # Extract segments with smaller duration for precise timing
        segments = self.extract_video_segments(video_path, segment_duration=segment_duration, overlap=3)
        
        if not segments:
            raise RuntimeError("No segments extracted from workout video")
        
        # Analyze each segment with workout-specific prompts
        print(f"\n🔍 Analyzing {len(segments)} workout segments...")
        workout_analyses = []
        
        for i, segment_path in enumerate(segments, 1):
            print(f"  🏋️  Analyzing workout segment {i}/{len(segments)}: {os.path.basename(segment_path)}")
            
            # Calculate timestamp for this segment
            segment_filename = os.path.basename(segment_path)
            # Extract start time from filename (format: segment_XXX_START-END.mp4)
            import re
            time_match = re.search(r'(\d+\.\d+)-(\d+\.\d+)s\.mp4', segment_filename)
            if time_match:
                start_timestamp = float(time_match.group(1))
                end_timestamp = float(time_match.group(2))
            else:
                # Fallback calculation
                start_timestamp = i * segment_duration
                end_timestamp = min(start_timestamp + segment_duration, total_duration)
            
            # Run workout-specific analysis
            analysis = self.analyze_workout_segment(segment_path, system_prompt, user_prompt)
            
            # Add timestamp information
            analysis.update({
                'start_timestamp': start_timestamp,
                'end_timestamp': end_timestamp,
                'duration': end_timestamp - start_timestamp,
                'timestamp_formatted': f"{self._format_timestamp(start_timestamp)} - {self._format_timestamp(end_timestamp)}"
            })
            
            workout_analyses.append(analysis)
            
            if analysis['analysis_success']:
                print(f"    ⏱️  Timestamp: {analysis['timestamp_formatted']}")
                print(f"    🏃 Exercise: {analysis['response'][:80]}...")
            
            time.sleep(0.5)  # Be nice to the system
        
        # Process results to identify exercise transitions and phases
        exercise_steps = self._identify_exercise_steps(workout_analyses)
        
        # Prepare results
        processing_time = time.time() - start_time
        
        results = {
            'video_path': video_path,
            'analysis_type': 'workout_with_timestamps',
            'processing_time_seconds': processing_time,
            'total_duration_seconds': total_duration,
            'fps': fps,
            'total_segments_analyzed': len(segments),
            'system_prompt': system_prompt,
            'user_prompt': user_prompt,
            'segment_analyses': workout_analyses,
            'exercise_steps': exercise_steps,
            'summary': {
                'total_exercises_identified': len(exercise_steps),
                'video_duration_formatted': self._format_timestamp(total_duration),
                'analysis_coverage': f"{len(workout_analyses)} segments"
            }
        }
        
        # Save results
        if output_file is None:
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            output_file = f"{video_name}_workout_timestamps.json"
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Print summary
        print(f"\n🎉 Workout Analysis with Timestamps Complete!")
        print(f"⏱️  Processing time: {processing_time:.1f} seconds")
        print(f"📊 Analyzed {len(segments)} segments covering {self._format_timestamp(total_duration)}")
        print(f"🏋️  Identified {len(exercise_steps)} exercise steps/phases")
        print(f"💾 Results saved to: {output_file}")
        
        if exercise_steps:
            print(f"\n🏆 Exercise Steps Identified:")
            for i, step in enumerate(exercise_steps[:10], 1):  # Show first 10
                print(f"  {i}. {step['timestamp_formatted']}: {step['exercise_name']}")
                print(f"     {step['description'][:100]}...")
        
        return results
    
    def analyze_workout_segment(self, segment_path: str, system_prompt: str, user_prompt: str) -> Dict:
        """
        Analyze a single workout video segment.
        
        Args:
            segment_path: Path to the video segment
            system_prompt: System prompt for workout analysis
            user_prompt: User prompt for specific requirements
        
        Returns:
            Dictionary with workout analysis results
        """
        # Run MLX-VLM analysis with workout-specific prompts
        cmd = [
            sys.executable, "-m", "mlx_vlm.smolvlm_video_generate",
            "--model", self.model_name,
            "--system", system_prompt,
            "--prompt", user_prompt,
            "--video", segment_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Parse the output to extract the actual response
            output_lines = result.stdout.strip().split('\n')
            
            # Find the actual response (after the separator)
            response_started = False
            response_lines = []
            
            for line in output_lines:
                if line.strip().startswith('=========='):
                    if response_started:
                        break
                    response_started = True
                    continue
                
                if response_started and line.strip():
                    # Skip metadata lines
                    if not any(skip in line for skip in ['Files:', 'Prompt:', 'tokens-per-sec', 'Peak memory:']):
                        response_lines.append(line.strip())
            
            response = ' '.join(response_lines).strip()
            
            # Extract exercise information
            exercise_info = self._extract_exercise_info(response)
            
            return {
                'segment_path': segment_path,
                'response': response,
                'exercise_name': exercise_info.get('exercise_name', 'Unknown Exercise'),
                'movement_phase': exercise_info.get('movement_phase', 'Unknown Phase'),
                'is_transition': exercise_info.get('is_transition', False),
                'analysis_success': True
            }
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Workout analysis failed for {segment_path}: {e}")
            return {
                'segment_path': segment_path,
                'response': f"Analysis failed: {e}",
                'exercise_name': 'Analysis Failed',
                'movement_phase': 'Unknown',
                'is_transition': False,
                'analysis_success': False
            }
    
    def _extract_exercise_info(self, response: str) -> Dict:
        """Extract exercise information from analysis response."""
        response_lower = response.lower()
        
        # Common exercise keywords
        exercises = {
            'push': ['push-up', 'push up', 'pushup'],
            'bench': ['bench press', 'bench'],
            'squat': ['squat'],
            'deadlift': ['deadlift'],
            'curl': ['curl', 'bicep'],
            'row': ['row'],
            'pull': ['pull-up', 'pull up', 'pullup'],
            'plank': ['plank'],
            'lunge': ['lunge'],
            'dip': ['dip'],
            'fly': ['fly', 'flye'],
            'press': ['press', 'overhead']
        }
        
        # Movement phases
        phases = {
            'setup': ['setup', 'starting', 'preparation', 'ready'],
            'execution': ['execution', 'performing', 'movement', 'rep', 'repetition'],
            'transition': ['transition', 'changing', 'moving to', 'switching'],
            'rest': ['rest', 'pause', 'break', 'recovery']
        }
        
        # Identify exercise
        exercise_name = 'Unknown Exercise'
        for exercise_type, keywords in exercises.items():
            if any(keyword in response_lower for keyword in keywords):
                exercise_name = exercise_type.title()
                break
        
        # Identify movement phase
        movement_phase = 'Unknown Phase'
        for phase_type, keywords in phases.items():
            if any(keyword in response_lower for keyword in keywords):
                movement_phase = phase_type.title()
                break
        
        # Check if this is a transition
        is_transition = any(word in response_lower for word in ['transition', 'changing', 'switching', 'moving to'])
        
        return {
            'exercise_name': exercise_name,
            'movement_phase': movement_phase,
            'is_transition': is_transition
        }
    
    def _identify_exercise_steps(self, analyses: List[Dict]) -> List[Dict]:
        """Identify distinct exercise steps from segment analyses."""
        steps = []
        current_exercise = None
        step_start = None
        
        for analysis in analyses:
            if not analysis['analysis_success']:
                continue
            
            exercise_name = analysis['exercise_name']
            
            # If this is a new exercise or first exercise
            if current_exercise != exercise_name:
                # Close previous step if exists
                if current_exercise is not None and step_start is not None:
                    steps.append({
                        'exercise_name': current_exercise,
                        'start_timestamp': step_start,
                        'end_timestamp': prev_analysis['end_timestamp'],
                        'duration': prev_analysis['end_timestamp'] - step_start,
                        'timestamp_formatted': f"{self._format_timestamp(step_start)} - {self._format_timestamp(prev_analysis['end_timestamp'])}",
                        'description': f"{current_exercise} exercise"
                    })
                
                # Start new step
                current_exercise = exercise_name
                step_start = analysis['start_timestamp']
            
            prev_analysis = analysis
        
        # Close final step
        if current_exercise is not None and step_start is not None:
            steps.append({
                'exercise_name': current_exercise,
                'start_timestamp': step_start,
                'end_timestamp': prev_analysis['end_timestamp'],
                'duration': prev_analysis['end_timestamp'] - step_start,
                'timestamp_formatted': f"{self._format_timestamp(step_start)} - {self._format_timestamp(prev_analysis['end_timestamp'])}",
                'description': f"{current_exercise} exercise"
            })
        
        return steps
    
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
            print(f"🧹 Cleaned up temporary files: {self.temp_dir}")

def main():
    """Demo the highlight generator."""
    
    # Check if we have our test video
    test_video = "/Users/jackmodesett/SmolVLM2/test_video.mp4"
    
    if not os.path.exists(test_video):
        print("❌ Test video not found. Creating a longer test video...")
        
        # Create a longer test video for highlight testing
        from create_test_video import create_test_video
        
        # Create a 10-second test video instead of 3 seconds
        import cv2
        import numpy as np
        
        output_path = "/Users/jackmodesett/SmolVLM2/long_test_video.mp4"
        width, height = 640, 480
        fps = 30
        duration = 10  # 10 seconds for better highlight testing
        total_frames = fps * duration
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        print(f"🎬 Creating longer test video: {output_path}")
        
        for frame_num in range(total_frames):
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            
            # Create different scenes for highlight detection
            progress = frame_num / total_frames
            
            if progress < 0.3:  # Scene 1: Calm movement
                bg_color = int(30 + 20 * np.sin(frame_num * 0.1))
                frame[:, :] = (bg_color, bg_color // 2, bg_color // 3)
                circle_x = int(width * 0.2 + (width * 0.3) * progress / 0.3)
                circle_y = int(height * 0.5)
                cv2.circle(frame, (circle_x, circle_y), 20, (0, 255, 0), -1)
                cv2.putText(frame, "Scene 1: Calm Movement", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
            elif progress < 0.6:  # Scene 2: Action sequence
                frame[:, :] = (100, 50, 50)  # Reddish background for action
                # Multiple moving objects
                circle_x = int(width * 0.5 + 100 * np.sin(frame_num * 0.3))
                circle_y = int(height * 0.3 + 50 * np.cos(frame_num * 0.3))
                cv2.circle(frame, (circle_x, circle_y), 25, (0, 255, 255), -1)
                
                rect_x = int(width * 0.7 - 150 * (progress - 0.3) / 0.3)
                rect_y = int(height * 0.7)
                cv2.rectangle(frame, (rect_x - 30, rect_y - 20), (rect_x + 30, rect_y + 20), (255, 0, 255), -1)
                
                cv2.putText(frame, "Scene 2: ACTION SEQUENCE!", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                cv2.putText(frame, "High Activity", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
                
            else:  # Scene 3: Calm ending
                bg_color = int(50 + 30 * np.sin(frame_num * 0.05))
                frame[:, :] = (bg_color // 3, bg_color // 2, bg_color)
                circle_x = int(width * 0.8)
                circle_y = int(height * 0.5 + 20 * np.sin(frame_num * 0.1))
                cv2.circle(frame, (circle_x, circle_y), 15, (255, 255, 255), -1)
                cv2.putText(frame, "Scene 3: Calm Ending", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Frame counter
            cv2.putText(frame, f"Frame {frame_num + 1}/{total_frames}", (10, height - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            out.write(frame)
        
        out.release()
        test_video = output_path
        print(f"✅ Created test video: {test_video}")
    
    # Run highlight generation
    generator = SmolVLMHighlightGenerator()
    
    try:
        results = generator.generate_highlights(
            video_path=test_video,
            min_significance=4,  # Lower threshold for demo
            max_highlights=5
        )
        
        print(f"\n📋 Highlight Generation Results:")
        print(f"🎬 Video: {results['video_path']}")
        print(f"⏱️  Processing: {results['processing_time_seconds']:.1f}s")
        print(f"📊 Segments: {results['total_segments_analyzed']}")
        print(f"🌟 Highlights: {results['highlights_found']}")
        
    except Exception as e:
        print(f"❌ Error during highlight generation: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        generator.cleanup()

if __name__ == "__main__":
    main()