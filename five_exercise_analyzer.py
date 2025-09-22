#!/usr/bin/env python3
"""
Enhanced workout analysis to isolate exactly 5 unique exercise timestamps
"""

import sys
import os
sys.path.append('/Users/jackmodesett/SmolVLM2')

from video_highlight_generator import SmolVLMHighlightGenerator
import json
from collections import defaultdict
import re

class FiveExerciseAnalyzer:
    """Specialized analyzer to extract exactly 5 distinct exercises from workout video."""
    
    def __init__(self):
        self.generator = SmolVLMHighlightGenerator()
    
    def analyze_for_five_exercises(self, video_path: str, target_exercises: int = 5):
        """
        Analyze workout video and consolidate into exactly 5 distinct exercises.
        
        Args:
            video_path: Path to workout video
            target_exercises: Number of exercises to isolate (default: 5)
        
        Returns:
            Dictionary with 5 distinct exercise blocks
        """
        print(f"🎯 Analyzing video to isolate {target_exercises} unique exercises...")
        
        # Run detailed analysis first
        system_prompt = """
        You are analyzing a workout video to identify distinct exercise types. 
        Focus on identifying when one exercise completely ends and a new one begins.
        Look for clear transitions between different movement patterns.
        Ignore small rest periods within the same exercise type.
        """
        
        user_prompt = f"Identify exactly {target_exercises} distinct exercises in this workout video with clear start and end points."
        
        # Use larger segments for better exercise boundary detection
        detailed_results = self.generator.analyze_workout_with_timestamps(
            video_path=video_path,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            segment_duration=30,  # Larger segments for better context
            output_file="detailed_five_exercise_analysis.json"
        )
        
        # Consolidate into 5 distinct exercises
        five_exercises = self._consolidate_to_five_exercises(
            detailed_results['segment_analyses'], 
            target_exercises
        )
        
        # Create final result
        final_result = {
            'video_path': video_path,
            'analysis_type': 'five_unique_exercises',
            'total_duration_seconds': detailed_results['total_duration_seconds'],
            'target_exercise_count': target_exercises,
            'exercises_found': len(five_exercises),
            'system_prompt': system_prompt,
            'user_prompt': user_prompt,
            'five_exercises': five_exercises,
            'summary': {
                'video_duration_formatted': detailed_results['summary']['video_duration_formatted'],
                'exercise_coverage': self._calculate_coverage(five_exercises, detailed_results['total_duration_seconds'])
            }
        }
        
        # Save results
        output_file = "five_unique_exercises.json"
        with open(output_file, 'w') as f:
            json.dump(final_result, f, indent=2)
        
        return final_result
    
    def _consolidate_to_five_exercises(self, segment_analyses, target_count=5):
        """Consolidate segment analyses into exactly 5 distinct exercises."""
        
        # Group segments by exercise type and time proximity
        exercise_groups = defaultdict(list)
        
        for analysis in segment_analyses:
            if analysis['analysis_success']:
                exercise_name = analysis['exercise_name']
                if exercise_name != 'Unknown Exercise':
                    exercise_groups[exercise_name].append(analysis)
        
        print(f"📊 Found exercise types: {list(exercise_groups.keys())}")
        
        # Create consolidated exercise blocks
        consolidated_exercises = []
        
        for exercise_name, segments in exercise_groups.items():
            if not segments:
                continue
                
            # Sort segments by start time
            segments.sort(key=lambda x: x['start_timestamp'])
            
            # Group segments into continuous blocks (merge if gap < 60 seconds)
            exercise_blocks = []
            current_block = [segments[0]]
            
            for segment in segments[1:]:
                # If gap between segments is small, merge them
                if segment['start_timestamp'] - current_block[-1]['end_timestamp'] <= 60:
                    current_block.append(segment)
                else:
                    # Save current block and start new one
                    exercise_blocks.append(current_block)
                    current_block = [segment]
            
            # Don't forget the last block
            if current_block:
                exercise_blocks.append(current_block)
            
            # Convert blocks to consolidated exercises
            for i, block in enumerate(exercise_blocks):
                start_time = block[0]['start_timestamp']
                end_time = block[-1]['end_timestamp']
                
                # Calculate duration and get representative description
                duration = end_time - start_time
                
                # Get the most detailed response from the block
                best_response = max(block, key=lambda x: len(x['response']))
                
                exercise_block = {
                    'exercise_number': len(consolidated_exercises) + 1,
                    'exercise_name': exercise_name,
                    'start_timestamp': start_time,
                    'end_timestamp': end_time,
                    'duration': duration,
                    'timestamp_formatted': f"{self._format_timestamp(start_time)} - {self._format_timestamp(end_time)}",
                    'description': best_response['response'][:200] + "...",
                    'segment_count': len(block),
                    'movement_phases': list(set([s['movement_phase'] for s in block if s['movement_phase'] != 'Unknown Phase']))
                }
                
                consolidated_exercises.append(exercise_block)
        
        # Sort by start time
        consolidated_exercises.sort(key=lambda x: x['start_timestamp'])
        
        # If we have more than target_count, select the longest/most significant ones
        if len(consolidated_exercises) > target_count:
            # Sort by duration (longest first) and take top target_count
            consolidated_exercises.sort(key=lambda x: x['duration'], reverse=True)
            consolidated_exercises = consolidated_exercises[:target_count]
            # Re-sort by start time
            consolidated_exercises.sort(key=lambda x: x['start_timestamp'])
        
        # If we have less than target_count, try to split long exercises
        elif len(consolidated_exercises) < target_count:
            consolidated_exercises = self._split_to_reach_target(consolidated_exercises, target_count)
        
        # Renumber exercises
        for i, exercise in enumerate(consolidated_exercises, 1):
            exercise['exercise_number'] = i
        
        return consolidated_exercises
    
    def _split_to_reach_target(self, exercises, target_count):
        """Split longer exercises to reach target count if needed."""
        
        while len(exercises) < target_count and exercises:
            # Find the longest exercise to split
            longest_exercise = max(exercises, key=lambda x: x['duration'])
            
            if longest_exercise['duration'] < 120:  # Don't split if less than 2 minutes
                break
            
            # Remove the longest and split it into two
            exercises.remove(longest_exercise)
            
            mid_point = longest_exercise['start_timestamp'] + (longest_exercise['duration'] / 2)
            
            # First half
            first_half = longest_exercise.copy()
            first_half['end_timestamp'] = mid_point
            first_half['duration'] = mid_point - first_half['start_timestamp']
            first_half['timestamp_formatted'] = f"{self._format_timestamp(first_half['start_timestamp'])} - {self._format_timestamp(mid_point)}"
            first_half['exercise_name'] = f"{longest_exercise['exercise_name']} (Part 1)"
            
            # Second half
            second_half = longest_exercise.copy()
            second_half['start_timestamp'] = mid_point
            second_half['duration'] = second_half['end_timestamp'] - mid_point
            second_half['timestamp_formatted'] = f"{self._format_timestamp(mid_point)} - {self._format_timestamp(second_half['end_timestamp'])}"
            second_half['exercise_name'] = f"{longest_exercise['exercise_name']} (Part 2)"
            
            exercises.extend([first_half, second_half])
            exercises.sort(key=lambda x: x['start_timestamp'])
        
        return exercises
    
    def _calculate_coverage(self, exercises, total_duration):
        """Calculate what percentage of video is covered by the 5 exercises."""
        total_exercise_time = sum(ex['duration'] for ex in exercises)
        coverage_percent = (total_exercise_time / total_duration) * 100
        return f"{coverage_percent:.1f}% ({self._format_timestamp(total_exercise_time)} of {self._format_timestamp(total_duration)})"
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds as MM:SS timestamp."""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"

def main():
    """Run the 5-exercise analysis."""
    
    workout_video = "/Users/jackmodesett/Downloads/chest workout.mov"
    
    if not os.path.exists(workout_video):
        print(f"❌ Workout video not found: {workout_video}")
        return
    
    analyzer = FiveExerciseAnalyzer()
    
    try:
        print(f"🏋️  Starting 5-exercise isolation analysis...")
        print(f"📹 Video: {workout_video}")
        
        results = analyzer.analyze_for_five_exercises(workout_video, target_exercises=5)
        
        print(f"\n🎯 Five Exercise Analysis Complete!")
        print(f"📊 Video Duration: {results['summary']['video_duration_formatted']}")
        print(f"🏋️  Exercises Found: {results['exercises_found']}")
        print(f"📈 Coverage: {results['summary']['exercise_coverage']}")
        
        print(f"\n🏆 Five Unique Exercises with Timestamps:")
        for exercise in results['five_exercises']:
            print(f"\n  {exercise['exercise_number']}. {exercise['exercise_name']}")
            print(f"     ⏱️  Time: {exercise['timestamp_formatted']} ({exercise['duration']:.0f}s)")
            print(f"     📝 Description: {exercise['description']}")
            if exercise['movement_phases']:
                print(f"     🔄 Phases: {', '.join(exercise['movement_phases'])}")
        
        print(f"\n✅ Detailed results saved to: five_unique_exercises.json")
        
    except Exception as e:
        print(f"❌ Error during 5-exercise analysis: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        analyzer.generator.cleanup()

if __name__ == "__main__":
    main()