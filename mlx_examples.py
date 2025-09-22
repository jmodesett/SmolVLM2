#!/usr/bin/env python3
"""
SmolVLM2 MLX Example Scripts
Comprehensive examples for using SmolVLM2 with MLX on Apple Silicon.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_mlx_command(command_args, description):
    """Run an MLX command and handle output."""
    print(f"\n🔄 {description}")
    print("=" * 60)
    
    try:
        result = subprocess.run(
            command_args,
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        if result.stderr:
            print("Warnings/Info:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False

def image_inference_example():
    """Example of image inference with MLX-VLM."""
    
    command = [
        sys.executable, "-m", "mlx_vlm.generate",
        "--model", "mlx-community/SmolVLM2-500M-Video-Instruct-mlx",
        "--image", "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/bee.jpg",
        "--prompt", "Can you describe this image in detail?"
    ]
    
    return run_mlx_command(command, "Image Inference Example - Bee on Flower")

def detailed_image_analysis_example():
    """Example of detailed image analysis."""
    
    command = [
        sys.executable, "-m", "mlx_vlm.generate",
        "--model", "mlx-community/SmolVLM2-500M-Video-Instruct-mlx",
        "--image", "https://huggingface.co/datasets/huggingface/documentation-images/resolve/0052a70beed5bf71b92610a43a52df6d286cd5f3/diffusers/rabbit.jpg",
        "--prompt", "What artistic style is this image? Describe the character, setting, and overall mood."
    ]
    
    return run_mlx_command(command, "Detailed Image Analysis Example - Artistic Rabbit")

def video_inference_example():
    """Example of video inference with system prompt."""
    
    video_path = "/Users/jackmodesett/SmolVLM2/test_video.mp4"
    
    if not os.path.exists(video_path):
        print(f"❌ Test video not found at {video_path}")
        print("Please run create_test_video.py first")
        return False
    
    command = [
        sys.executable, "-m", "mlx_vlm.smolvlm_video_generate",
        "--model", "mlx-community/SmolVLM2-500M-Video-Instruct-mlx",
        "--system", "Focus only on describing the key dramatic action or notable event occurring in this video segment. Skip general context or scene-setting details unless they are crucial to understanding the main action.",
        "--prompt", "What is happening in this video?",
        "--video", video_path
    ]
    
    return run_mlx_command(command, "Video Inference Example - Test Video Analysis")

def video_summary_example():
    """Example of video summarization with different system prompt."""
    
    video_path = "/Users/jackmodesett/SmolVLM2/test_video.mp4"
    
    if not os.path.exists(video_path):
        print(f"❌ Test video not found at {video_path}")
        print("Please run create_test_video.py first")
        return False
    
    command = [
        sys.executable, "-m", "mlx_vlm.smolvlm_video_generate",
        "--model", "mlx-community/SmolVLM2-500M-Video-Instruct-mlx",
        "--system", "Provide a concise one-sentence summary of what happens in this video.",
        "--prompt", "Summarize this video in one sentence.",
        "--video", video_path
    ]
    
    return run_mlx_command(command, "Video Summary Example - One Sentence Summary")

def create_usage_guide():
    """Create a usage guide file."""
    
    guide_content = """# SmolVLM2 Usage Guide

## Installation Complete! 🎉

You have successfully installed SmolVLM2 with both Transformers and MLX support.

## Available Models

### Transformers (GPU/CPU/MPS)
- `HuggingFaceTB/SmolVLM2-2.2B-Instruct` - Best for vision and video tasks
- `HuggingFaceTB/SmolVLM2-500M-Video-Instruct` - Smaller video model
- `HuggingFaceTB/SmolVLM2-256M-Video-Instruct` - Smallest experimental model

### MLX (Apple Silicon Optimized)
- `mlx-community/SmolVLM2-500M-Video-Instruct-mlx` - Optimized for Apple Silicon

## Quick Usage Examples

### Image Inference with MLX (Command Line)
```bash
python -m mlx_vlm.generate \\
  --model mlx-community/SmolVLM2-500M-Video-Instruct-mlx \\
  --image path/to/image.jpg \\
  --prompt "Describe this image"
```

### Video Inference with MLX (Command Line)
```bash
python -m mlx_vlm.smolvlm_video_generate \\
  --model mlx-community/SmolVLM2-500M-Video-Instruct-mlx \\
  --system "Focus on the main action in the video" \\
  --prompt "What is happening?" \\
  --video path/to/video.mp4
```

### Python Script with Transformers
```python
from transformers import AutoProcessor, AutoModelForImageTextToText
import torch
from PIL import Image

# Load model
processor = AutoProcessor.from_pretrained("HuggingFaceTB/SmolVLM2-2.2B-Instruct")
model = AutoModelForImageTextToText.from_pretrained(
    "HuggingFaceTB/SmolVLM2-2.2B-Instruct",
    torch_dtype=torch.float32,  # Use float32 for MPS
    device_map=None,
).to("mps")  # or "cuda" or "cpu"

# Prepare conversation
messages = [
    {
        "role": "user",
        "content": [
            {"type": "image", "image": your_image},
            {"type": "text", "text": "Describe this image"}
        ]
    },
]

# Generate response
inputs = processor.apply_chat_template(messages, return_tensors="pt")
inputs = {k: v.to("mps") for k, v in inputs.items()}

with torch.no_grad():
    generated_ids = model.generate(**inputs, max_new_tokens=150)

response = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
```

## System Prompts for Video Understanding

Different system prompts can drastically change the model's behavior:

1. **Detailed Analysis**: "Describe all scenes and transitions in detail."
2. **Action Focus**: "Focus only on describing the key dramatic action."
3. **Summary**: "Provide a concise one-sentence summary."
4. **Technical**: "Describe the technical aspects like camera movements and lighting."

## Test Files in This Directory

- `test_transformers_mps.py` - Test transformers with MPS compatibility
- `test_video.mp4` - Sample test video for video inference
- `create_test_video.py` - Script to create test videos
- `mlx_examples.py` - This file with comprehensive examples

## Performance Notes

- **MLX** is optimized for Apple Silicon and provides excellent performance
- **Transformers with MPS** works well but may be slower than MLX
- **Transformers with CUDA** (if available) provides good performance
- Use smaller models (500M, 256M) for faster inference on limited hardware

## Troubleshooting

1. **Import Errors**: Make sure you're using the virtual environment
2. **Memory Issues**: Try smaller models or reduce max_new_tokens
3. **MPS Errors**: Use torch.float32 instead of bfloat16 for MPS
4. **Video Issues**: Ensure video file exists and is in supported format

Enjoy using SmolVLM2! 🚀
"""
    
    with open("/Users/jackmodesett/SmolVLM2/USAGE_GUIDE.md", "w") as f:
        f.write(guide_content)
    
    print("📖 Created comprehensive usage guide: USAGE_GUIDE.md")

def main():
    """Run all example demonstrations."""
    print("🚀 SmolVLM2 MLX Examples and Demonstrations")
    print("=" * 60)
    
    examples = [
        ("Image Inference", image_inference_example),
        ("Detailed Image Analysis", detailed_image_analysis_example),
        ("Video Inference", video_inference_example),
        ("Video Summary", video_summary_example),
    ]
    
    results = {}
    
    for name, example_func in examples:
        success = example_func()
        results[name] = "✅ Success" if success else "❌ Failed"
    
    print("\n" + "=" * 60)
    print("📊 Example Results Summary:")
    for name, result in results.items():
        print(f"  {result} {name}")
    
    # Create usage guide
    create_usage_guide()
    
    print("\n🎉 All examples completed! Check USAGE_GUIDE.md for more information.")

if __name__ == "__main__":
    main()