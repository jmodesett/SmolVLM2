#!/usr/bin/env python3
"""
SmolVLM2 Video Inference with Transformers
Complete example showing video understanding with the transformers library.
"""

import torch
from transformers import AutoProcessor, AutoModelForImageTextToText
import av
import numpy as np
from PIL import Image
import requests
import tempfile
import os

def check_device():
    """Check available devices and return the best one."""
    if torch.cuda.is_available():
        device = "cuda"
        print(f"✅ CUDA available: {torch.cuda.get_device_name()}")
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device = "mps"
        print("✅ MPS (Apple Silicon) available")
    else:
        device = "cpu"
        print("⚠️  Using CPU (this will be slow)")
    return device

def load_model(model_name="HuggingFaceTB/SmolVLM2-2.2B-Instruct"):
    """Load the SmolVLM2 model and processor."""
    print(f"🔄 Loading model: {model_name}")
    
    device = check_device()
    
    try:
        processor = AutoProcessor.from_pretrained(model_name)
        
        # Use float32 for MPS and CPU to avoid dtype issues
        if device == "mps" or device == "cpu":
            torch_dtype = torch.float32
        else:  # CUDA
            torch_dtype = torch.bfloat16
        
        model = AutoModelForImageTextToText.from_pretrained(
            model_name,
            torch_dtype=torch_dtype,
            device_map=None,  # Don't use device_map for MPS
        ).to(device)
        
        print(f"✅ Model loaded successfully on {device} with dtype {torch_dtype}")
        return model, processor, device
        
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return None, None, None

def test_video_inference(model, processor, device):
    """Test video understanding with SmolVLM2."""
    print("\n🎬 Testing Video Inference...")
    
    video_path = "/Users/jackmodesett/SmolVLM2/test_video.mp4"
    
    if not os.path.exists(video_path):
        print(f"❌ Video file not found: {video_path}")
        print("Please run create_test_video.py first to create a test video.")
        return
    
    try:
        # Prepare the conversation with video
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "video", "path": video_path},
                    {"type": "text", "text": "Describe what happens in this video in detail."}
                ]
            },
        ]
        
        # Apply chat template and process
        inputs = processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        
        # Move inputs to device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Generate response
        print("🔄 Generating response...")
        with torch.no_grad():
            generated_ids = model.generate(**inputs, do_sample=False, max_new_tokens=200)
        
        generated_texts = processor.batch_decode(
            generated_ids,
            skip_special_tokens=True,
        )
        
        print("✅ Video inference successful!")
        print(f"Response: {generated_texts[0]}")
        
    except Exception as e:
        print(f"❌ Error in video inference: {e}")
        import traceback
        traceback.print_exc()

def test_video_with_system_prompt(model, processor, device):
    """Test video understanding with system prompt."""
    print("\n🎬 Testing Video Inference with System Prompt...")
    
    video_path = "/Users/jackmodesett/SmolVLM2/test_video.mp4"
    
    if not os.path.exists(video_path):
        print(f"❌ Video file not found: {video_path}")
        return
    
    try:
        # Prepare the conversation with system message and video
        messages = [
            {
                "role": "system",
                "content": "Focus only on describing the key movements and actions happening in this video. Be concise and specific about what objects are moving and how."
            },
            {
                "role": "user",
                "content": [
                    {"type": "video", "path": video_path},
                    {"type": "text", "text": "What movements do you see in this video?"}
                ]
            },
        ]
        
        # Apply chat template and process
        inputs = processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        
        # Move inputs to device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Generate response
        print("🔄 Generating response with system prompt...")
        with torch.no_grad():
            generated_ids = model.generate(**inputs, do_sample=False, max_new_tokens=150)
        
        generated_texts = processor.batch_decode(
            generated_ids,
            skip_special_tokens=True,
        )
        
        print("✅ Video inference with system prompt successful!")
        print(f"Response: {generated_texts[0]}")
        
    except Exception as e:
        print(f"❌ Error in video inference with system prompt: {e}")
        import traceback
        traceback.print_exc()

def test_image_and_video_combination(model, processor, device):
    """Test understanding both image and video in one conversation."""
    print("\n🖼️🎬 Testing Combined Image and Video Understanding...")
    
    video_path = "/Users/jackmodesett/SmolVLM2/test_video.mp4"
    
    if not os.path.exists(video_path):
        print(f"❌ Video file not found: {video_path}")
        return
    
    try:
        # Load a sample image
        image_url = "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/bee.jpg"
        image = Image.open(requests.get(image_url, stream=True).raw)
        
        # Prepare the conversation with both image and video
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "I'm showing you an image and a video. Please compare them:"},
                    {"type": "image", "image": image},
                    {"type": "video", "path": video_path},
                    {"type": "text", "text": "What are the main differences between the content in the image and the video?"}
                ]
            },
        ]
        
        # Apply chat template and process
        inputs = processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        
        # Move inputs to device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Generate response
        print("🔄 Generating response for combined media...")
        with torch.no_grad():
            generated_ids = model.generate(**inputs, do_sample=False, max_new_tokens=200)
        
        generated_texts = processor.batch_decode(
            generated_ids,
            skip_special_tokens=True,
        )
        
        print("✅ Combined image and video inference successful!")
        print(f"Response: {generated_texts[0]}")
        
    except Exception as e:
        print(f"❌ Error in combined inference: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function to run all video tests."""
    print("🚀 SmolVLM2 Video Inference with Transformers")
    print("=" * 60)
    
    # Load model
    model, processor, device = load_model()
    
    if model is None:
        print("❌ Failed to load model. Exiting.")
        return
    
    # Run all tests
    test_video_inference(model, processor, device)
    test_video_with_system_prompt(model, processor, device)
    test_image_and_video_combination(model, processor, device)
    
    print("\n✅ All video tests completed!")
    print("\n💡 Tips:")
    print("  - Use system prompts to guide the model's focus")
    print("  - Shorter videos generally work better")
    print("  - The model can handle multiple media types in one conversation")

if __name__ == "__main__":
    main()