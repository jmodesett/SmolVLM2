#!/usr/bin/env python3
"""
Test the enhanced workout timestamp analysis functionality
"""

import sys
import os
sys.path.append('/Users/jackmodesett/SmolVLM2')

from video_highlight_generator import SmolVLMHighlightGenerator

def test_workout_timestamps():
    """Test the new workout timestamp analysis method."""
    
    # Path to the chest workout video
    workout_video = "/Users/jackmodesett/Downloads/chest workout.mov"
    
    if not os.path.exists(workout_video):
        print(f"❌ Workout video not found: {workout_video}")
        return
    
    print(f"🏋️  Testing workout timestamp analysis...")
    print(f"📹 Video: {workout_video}")
    
    # Create the generator
    generator = SmolVLMHighlightGenerator()
    
    try:
        # Test with the exact system prompt requested
        system_prompt = "Splice the video into steps between the displayed excercise with a short summary of what the movement is"
        user_prompt = "This is a workout video please break it into 5 steps"
        
        # Run the enhanced workout analysis
        results = generator.analyze_workout_with_timestamps(
            video_path=workout_video,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            segment_duration=15,  # 15-second segments for good granularity
            output_file="chest_workout_timestamps.json"
        )
        
        print(f"\n📋 Workout Timestamp Analysis Results:")
        print(f"🎬 Video: {results['video_path']}")
        print(f"⏱️  Total Duration: {results['summary']['video_duration_formatted']}")
        print(f"📊 Segments Analyzed: {results['total_segments_analyzed']}")
        print(f"🏋️  Exercise Steps: {results['summary']['total_exercises_identified']}")
        print(f"⏱️  Processing Time: {results['processing_time_seconds']:.1f}s")
        
        # Show detailed exercise steps with timestamps
        if results['exercise_steps']:
            print(f"\n🎯 Exercise Steps with Timestamps:")
            for i, step in enumerate(results['exercise_steps'], 1):
                print(f"  {i}. {step['timestamp_formatted']}: {step['exercise_name']}")
                print(f"     Duration: {step['duration']:.1f}s")
                print(f"     Description: {step['description']}")
                print()
        
        # Show some segment details
        print(f"\n📝 Sample Segment Analysis:")
        for i, analysis in enumerate(results['segment_analyses'][:3], 1):
            if analysis['analysis_success']:
                print(f"  Segment {i}: {analysis['timestamp_formatted']}")
                print(f"    Exercise: {analysis['exercise_name']}")
                print(f"    Phase: {analysis['movement_phase']}")
                print(f"    Analysis: {analysis['response'][:120]}...")
                print()
        
        print(f"✅ Full results saved to: chest_workout_timestamps.json")
        
    except Exception as e:
        print(f"❌ Error during workout timestamp analysis: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        generator.cleanup()

if __name__ == "__main__":
    test_workout_timestamps()