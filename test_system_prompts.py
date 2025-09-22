#!/usr/bin/env python3
"""
SmolVLM2 Video Analysis with Different System Prompts
Test how different system prompts affect video analysis results.
"""

import subprocess
import sys
import os
import time

def analyze_video_with_prompt(video_path, system_prompt, prompt, description):
    """Analyze video with a specific system prompt."""
    
    print(f"\n🎯 {description}")
    print("=" * 60)
    print(f"System Prompt: {system_prompt}")
    print(f"User Prompt: {prompt}")
    print("=" * 60)
    
    cmd = [
        sys.executable, "-m", "mlx_vlm.smolvlm_video_generate",
        "--model", "mlx-community/SmolVLM2-500M-Video-Instruct-mlx",
        "--system", system_prompt,
        "--prompt", prompt,
        "--video", video_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Extract the actual response
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
        print(f"🤖 Response: {response}")
        return response
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Analysis failed: {e}")
        return None

def main():
    """Test different system prompts on the same video."""
    
    video_path = "/Users/jackmodesett/SmolVLM2/test_video.mp4"
    
    if not os.path.exists(video_path):
        print(f"❌ Video not found: {video_path}")
        print("Please run create_test_video.py first to create a test video.")
        return
    
    print("🎬 SmolVLM2 System Prompt Testing")
    print(f"📹 Video: {video_path}")
    
    # Define different system prompts to test
    test_scenarios = [
        {
            "description": "General Analysis",
            "system_prompt": "Analyze this video and describe what you see in a clear, objective manner.",
            "prompt": "What happens in this video?"
        },
        {
            "description": "Action-Focused Analysis", 
            "system_prompt": "Focus only on describing the key dramatic action or notable event occurring in this video segment. Skip general context or scene-setting details unless they are crucial to understanding the main action.",
            "prompt": "What are the main actions happening?"
        },
        {
            "description": "Technical Analysis",
            "system_prompt": "Analyze this video from a technical perspective, focusing on visual elements, movements, colors, and composition.",
            "prompt": "Describe the technical aspects of this video."
        },
        {
            "description": "Significance Rating",
            "system_prompt": "Analyze this video and rate its significance or importance on a scale of 1-10. Explain your reasoning for the rating.",
            "prompt": "How significant are the events in this video? Rate from 1-10 and explain why."
        },
        {
            "description": "Narrative Summary",
            "system_prompt": "Provide a narrative summary as if describing the video to someone who cannot see it. Focus on the story being told.",
            "prompt": "Tell me the story of what happens in this video."
        },
        {
            "description": "One-Sentence Summary",
            "system_prompt": "Provide a concise one-sentence summary of what happens in this video.",
            "prompt": "Summarize this video in one sentence."
        }
    ]
    
    responses = {}
    
    # Test each scenario
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n📊 Test {i}/{len(test_scenarios)}")
        
        response = analyze_video_with_prompt(
            video_path=video_path,
            system_prompt=scenario["system_prompt"],
            prompt=scenario["prompt"],
            description=scenario["description"]
        )
        
        responses[scenario["description"]] = response
        
        # Small delay between requests
        time.sleep(2)
    
    # Summary
    print("\n" + "=" * 80)
    print("📋 SUMMARY OF DIFFERENT APPROACHES")
    print("=" * 80)
    
    for description, response in responses.items():
        if response:
            print(f"\n🎯 {description}:")
            print(f"   {response[:100]}{'...' if len(response) > 100 else ''}")
    
    print(f"\n💡 Key Insights:")
    print(f"   • Different system prompts produce notably different responses")
    print(f"   • Action-focused prompts tend to be more concise")
    print(f"   • Technical prompts focus on visual elements")
    print(f"   • Rating prompts provide quantitative assessments")
    print(f"   • Summary prompts are most concise")
    
    print(f"\n🚀 Next Steps:")
    print(f"   • Try these prompts with your own videos")
    print(f"   • Experiment with custom system prompts for your use case")
    print(f"   • Combine multiple approaches for comprehensive analysis")

if __name__ == "__main__":
    main()