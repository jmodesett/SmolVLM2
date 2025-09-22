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