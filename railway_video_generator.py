#!/usr/bin/env python3
"""
Railway-compatible Video Highlight Generator
Uses transformers instead of MLX for cross-platform deployment
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
import torch
from transformers import AutoProcessor, AutoModelForImageTextToText

class RailwayVideoHighlightGenerator:
    """
    Railway-compatible video highlight generator using transformers.
    
    This version uses transformers instead of MLX for Railway deployment compatibility.
    """
    
    def __init__(self, model_name="HuggingFaceTB/SmolVLM2-500M-Video-Instruct"):
        self.model_name = model_name
        self.temp_dir = tempfile.mkdtemp(prefix="smolvlm_highlights_")
        self.processor = None
        self.model = None
        self.device = self._get_device()
        self._load_model()
        print(f"🎬 Railway SmolVLM2 Video Highlight Generator")
        print(f"📁 Temporary files: {self.temp_dir}")
        print(f"🔧 Device: {self.device}")
    
    def _get_device(self):
        """Get the best available device for Railway deployment."""
        if torch.cuda.is_available():
            return "cuda"
        else:
            return "cpu"  # Railway typically provides CPU instances
    
    def _load_model(self):
        """Load the SmolVLM2 model with transformers."""
        try:
            print(f"🔄 Loading model: {self.model_name}")
            
            self.processor = AutoProcessor.from_pretrained(self.model_name)
            
            # Use appropriate dtype for the device
            torch_dtype = torch.float32 if self.device == "cpu" else torch.bfloat16
            
            self.model = AutoModelForImageTextToText.from_pretrained(
                self.model_name,
                torch_dtype=torch_dtype,
                device_map="auto" if self.device == "cuda" else None,
            )
            
            if self.device == "cpu":
                self.model = self.model.to(self.device)
            
            print(f"✅ Model loaded successfully on {self.device}")
            
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            raise
    
    def analyze_video_with_transformers(self, video_path: str, system_prompt: str, user_prompt: str) -> Dict:
        """
        Analyze video using transformers instead of MLX command line.
        
        Args:
            video_path: Path to video file
            system_prompt: System prompt for analysis
            user_prompt: User prompt for analysis
        
        Returns:
            Dictionary with analysis results
        """
        try:
            # Prepare messages for the model
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
            
            # Apply chat template
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
                generated_ids = self.model.generate(
                    **inputs, 
                    do_sample=False, 
                    max_new_tokens=200,
                    pad_token_id=self.processor.tokenizer.eos_token_id
                )
            
            # Decode response
            generated_texts = self.processor.batch_decode(
                generated_ids,
                skip_special_tokens=True,
            )
            
            response = generated_texts[0] if generated_texts else "Analysis failed"
            
            return {
                'segment_path': video_path,
                'response': response,
                'significance_score': self._extract_significance_score(response),
                'analysis_success': True
            }
            
        except Exception as e:
            print(f"❌ Transformers analysis failed for {video_path}: {e}")
            return {
                'segment_path': video_path,
                'response': f"Analysis failed: {e}",
                'significance_score': 0,
                'analysis_success': False
            }
    
    # Keep all other methods from the original class but modify analyze_segment
    def analyze_segment(self, segment_path: str, system_prompt: str = None) -> Dict:
        """Analyze a video segment using transformers."""
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
        
        return self.analyze_video_with_transformers(segment_path, system_prompt, prompt)
    
    def analyze_workout_segment(self, segment_path: str, system_prompt: str, user_prompt: str) -> Dict:
        """Analyze a single workout video segment using transformers."""
        try:
            analysis = self.analyze_video_with_transformers(segment_path, system_prompt, user_prompt)
            
            if analysis['analysis_success']:
                # Extract exercise information
                exercise_info = self._extract_exercise_info(analysis['response'])
                
                analysis.update({
                    'exercise_name': exercise_info.get('exercise_name', 'Unknown Exercise'),
                    'movement_phase': exercise_info.get('movement_phase', 'Unknown Phase'),
                    'is_transition': exercise_info.get('is_transition', False)
                })
            
            return analysis
            
        except Exception as e:
            print(f"❌ Workout analysis failed for {segment_path}: {e}")
            return {
                'segment_path': segment_path,
                'response': f"Analysis failed: {e}",
                'exercise_name': 'Analysis Failed',
                'movement_phase': 'Unknown',
                'is_transition': False,
                'analysis_success': False
            }
