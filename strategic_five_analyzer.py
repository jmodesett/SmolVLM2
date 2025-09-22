#!/usr/bin/env python3
"""
Manual 5-exercise isolation using strategic time sampling
"""

import sys
import os
import subprocess
sys.path.append('/Users/jackmodesett/SmolVLM2')

from video_highlight_generator import SmolVLMHighlightGenerator
import json

class ManualFiveExerciseAnalyzer:
    """Manually sample video at strategic intervals to identify 5 distinct exercises."""
    
    def __init__(self):
        self.generator = SmolVLMHighlightGenerator()
    
    def analyze_five_strategic_points(self, video_path: str, total_duration: float):
        """
        Sample video at 5 strategic time points to identify distinct exercises.
        
        Args:
            video_path: Path to workout video
            total_duration: Total video duration in seconds
        
        Returns:
            Dictionary with 5 distinct exercise blocks
        """
        print(f"🎯 Strategically sampling video at 5 time points for distinct exercises...")
        
        # Calculate 5 strategic time points (avoiding start/end, evenly distributed)
        start_buffer = 60  # Skip first minute (intro/setup)
        end_buffer = 60    # Skip last minute (outro/cooldown)
        analysis_window = total_duration - start_buffer - end_buffer
        
        # 5 strategic sampling points
        sample_points = []
        for i in range(5):
            time_point = start_buffer + (i * analysis_window / 4)  # Divide into 4 intervals for 5 points
            sample_points.append(time_point)
        
        print(f"📍 Sampling at these time points:")
        for i, point in enumerate(sample_points, 1):
            print(f"   {i}. {self._format_timestamp(point)} ({point:.0f}s)")
        
        # Analyze each strategic point with longer context
        exercises = []
        
        for i, sample_time in enumerate(sample_points, 1):
            # Create a 2-minute window around each sample point
            start_time = max(0, sample_time - 60)
            end_time = min(total_duration, sample_time + 60)
            
            print(f"\n🔍 Analyzing Exercise {i} around {self._format_timestamp(sample_time)}...")
            
            # Extract segment for this exercise
            segment_path = self._extract_specific_segment(video_path, start_time, end_time, i)
            
            if segment_path:
                # Analyze this specific segment
                analysis = self._analyze_exercise_segment(segment_path, i, start_time, end_time)
                exercises.append(analysis)
        
        # Create final result
        final_result = {
            'video_path': video_path,
            'analysis_type': 'five_strategic_exercises',
            'total_duration_seconds': total_duration,
            'sampling_strategy': 'strategic_time_points',
            'sample_points': sample_points,
            'exercises_found': len(exercises),
            'five_exercises': exercises,
            'summary': {
                'video_duration_formatted': self._format_timestamp(total_duration),
                'total_exercise_time': sum(ex['duration'] for ex in exercises),
                'average_exercise_duration': sum(ex['duration'] for ex in exercises) / len(exercises) if exercises else 0
            }
        }
        
        # Save results
        output_file = "five_strategic_exercises.json"
        with open(output_file, 'w') as f:
            json.dump(final_result, f, indent=2)
        
        return final_result
    
    def _extract_specific_segment(self, video_path: str, start_time: float, end_time: float, exercise_num: int) -> str:
        """Extract a specific time segment from the video."""
        import tempfile
        
        # Create segment filename
        segment_filename = f"exercise_{exercise_num}_{start_time:.0f}-{end_time:.0f}s.mp4"
        segment_path = os.path.join(self.generator.temp_dir, segment_filename)
        
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
            print(f"  ✅ Extracted: {segment_filename}")
            return segment_path
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to extract segment: {e}")
            return ""  # Return empty string instead of None
    
    def _analyze_exercise_segment(self, segment_path: str, exercise_num: int, start_time: float, end_time: float) -> dict:
        """Analyze a specific exercise segment."""
        
        system_prompt = f"""
        You are analyzing Exercise {exercise_num} from a workout video. 
        This segment should contain ONE distinct exercise type.
        Identify the PRIMARY exercise being performed and ignore any transitions or brief rests.
        Focus on the main movement pattern and provide a clear exercise name.
        """
        
        user_prompt = f"What is the main exercise being performed in this segment? Provide a clear, specific exercise name and describe the movement."
        
        # Run MLX-VLM analysis
        cmd = [
            sys.executable, "-m", "mlx_vlm.smolvlm_video_generate",
            "--model", self.generator.model_name,
            "--system", system_prompt,
            "--prompt", user_prompt,
            "--video", segment_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Parse the output
            output_lines = result.stdout.strip().split('\n')
            response_started = False
            response_lines = []
            
            for line in output_lines:
                if line.strip().startswith('=========='):
                    if response_started:
                        break
                    response_started = True
                    continue
                
                if response_started and line.strip():
                    if not any(skip in line for skip in ['Files:', 'Prompt:', 'tokens-per-sec', 'Peak memory:']):
                        response_lines.append(line.strip())
            
            response = ' '.join(response_lines).strip()
            
            # Extract exercise name from response
            exercise_name = self._extract_primary_exercise_name(response)
            
            exercise_info = {
                'exercise_number': exercise_num,
                'exercise_name': exercise_name,
                'start_timestamp': start_time,
                'end_timestamp': end_time,
                'duration': end_time - start_time,
                'timestamp_formatted': f"{self._format_timestamp(start_time)} - {self._format_timestamp(end_time)}",
                'description': response,
                'analysis_success': True,
                'segment_path': segment_path
            }
            
            print(f"  🏋️  Identified: {exercise_name}")
            print(f"  ⏱️  Duration: {exercise_info['duration']:.0f}s")
            print(f"  📝 Analysis: {response[:80]}...")
            
            return exercise_info
            
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Analysis failed: {e}")
            return {
                'exercise_number': exercise_num,
                'exercise_name': 'Analysis Failed',
                'start_timestamp': start_time,
                'end_timestamp': end_time,
                'duration': end_time - start_time,
                'timestamp_formatted': f"{self._format_timestamp(start_time)} - {self._format_timestamp(end_time)}",
                'description': f"Analysis failed: {e}",
                'analysis_success': False,
                'segment_path': segment_path
            }
    
    def _extract_primary_exercise_name(self, response: str) -> str:
        """Extract the primary exercise name from the analysis response."""
        response_lower = response.lower()
        
        # Common exercise patterns to look for
        exercise_patterns = {
            'bench press': ['bench press', 'bench pressing', 'pressing'],
            'push-ups': ['push-up', 'push up', 'pushup', 'push-ups'],
            'squats': ['squat', 'squatting'],
            'deadlift': ['deadlift', 'deadlifting'],
            'bicep curls': ['bicep curl', 'curl', 'curling'],
            'rows': ['row', 'rowing'],
            'pull-ups': ['pull-up', 'pull up', 'pullup'],
            'planks': ['plank', 'planking'],
            'lunges': ['lunge', 'lunging'],
            'chest fly': ['fly', 'flye', 'chest fly'],
            'shoulder press': ['shoulder press', 'overhead press', 'press'],
            'tricep extension': ['tricep', 'triceps'],
            'lat pulldown': ['lat pulldown', 'pulldown'],
            'dips': ['dip', 'dipping']
        }
        
        # Look for exercise patterns in the response
        for exercise_name, patterns in exercise_patterns.items():
            if any(pattern in response_lower for pattern in patterns):
                return exercise_name.title()
        
        # If no specific pattern found, try to extract from first sentence
        sentences = response.split('.')
        if sentences:
            first_sentence = sentences[0].lower()
            # Look for "performing X" or "doing X" patterns
            import re
            exercise_match = re.search(r'(?:performing|doing|executing)\s+([a-zA-Z\s]+)', first_sentence)
            if exercise_match:
                return exercise_match.group(1).strip().title()
        
        return "Unidentified Exercise"
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds as MM:SS timestamp."""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"

def main():
    """Run the strategic 5-exercise analysis."""
    
    workout_video = "/Users/jackmodesett/Downloads/chest workout.mov"
    
    if not os.path.exists(workout_video):
        print(f"❌ Workout video not found: {workout_video}")
        return
    
    # Get video duration
    import cv2
    cap = cv2.VideoCapture(workout_video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    total_duration = total_frames / fps
    cap.release()
    
    analyzer = ManualFiveExerciseAnalyzer()
    
    try:
        print(f"🏋️  Starting strategic 5-exercise analysis...")
        print(f"📹 Video: {workout_video}")
        print(f"⏱️  Duration: {analyzer._format_timestamp(total_duration)} ({total_duration:.1f}s)")
        
        results = analyzer.analyze_five_strategic_points(workout_video, total_duration)
        
        print(f"\n🎯 Strategic Five Exercise Analysis Complete!")
        print(f"📊 Video Duration: {results['summary']['video_duration_formatted']}")
        print(f"🏋️  Exercises Found: {results['exercises_found']}")
        print(f"⏱️  Total Exercise Time: {analyzer._format_timestamp(results['summary']['total_exercise_time'])}")
        print(f"📈 Average Exercise Duration: {results['summary']['average_exercise_duration']:.0f}s")
        
        print(f"\n🏆 Five Strategic Exercises with Timestamps:")
        for exercise in results['five_exercises']:
            print(f"\n  {exercise['exercise_number']}. {exercise['exercise_name']}")
            print(f"     ⏱️  Time: {exercise['timestamp_formatted']} ({exercise['duration']:.0f}s)")
            print(f"     📝 Description: {exercise['description'][:120]}...")
        
        print(f"\n✅ Results saved to: five_strategic_exercises.json")
        
    except Exception as e:
        print(f"❌ Error during strategic analysis: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        analyzer.generator.cleanup()

if __name__ == "__main__":
    main()