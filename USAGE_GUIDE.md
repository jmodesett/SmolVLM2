# SmolVLM2 Usage Guide

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
python -m mlx_vlm.generate \
  --model mlx-community/SmolVLM2-500M-Video-Instruct-mlx \
  --image path/to/image.jpg \
  --prompt "Describe this image"
```

### Video Inference with MLX (Command Line)
```bash
python -m mlx_vlm.smolvlm_video_generate \
  --model mlx-community/SmolVLM2-500M-Video-Instruct-mlx \
  --system "Focus on the main action in the video" \
  --prompt "What is happening?" \
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
