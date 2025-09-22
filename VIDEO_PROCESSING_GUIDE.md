# SmolVLM2 Video Processing Guide 🎬

## Overview

Based on the [SmolVLM2 blog post](https://huggingface.co/blog/smolvlm2) and our implementation, SmolVLM2 excels at video understanding and can process long-form videos for highlight extraction. Here's a comprehensive guide for video processing.

## 🎯 Video Processing Capabilities

### According to HuggingFace Blog:
- **Long-form video processing**: Handles 1+ hours of video content
- **Highlight extraction**: Automatically identifies significant moments
- **Soccer match analysis**: Tested extensively with sports content
- **Content summarization**: Creates summaries of lengthy events

### Our Tested Capabilities:
- ✅ **Short video analysis** (3-30 seconds)
- ✅ **Motion detection** and scene understanding
- ✅ **Segment-based processing** for longer videos
- ✅ **Significance scoring** (1-10 scale)
- ✅ **System prompt guidance** for focused analysis

## 🛠️ Available Tools

### 1. **MLX Command Line (Recommended for Apple Silicon)**

#### Single Video Analysis:
```bash
python -m mlx_vlm.smolvlm_video_generate \\
  --model mlx-community/SmolVLM2-500M-Video-Instruct-mlx \\
  --system "Focus on identifying key actions and significant events" \\
  --prompt "What are the most important moments in this video?" \\
  --video path/to/your/video.mp4
```

#### With Custom System Prompts:
```bash
# For Sports Analysis
python -m mlx_vlm.smolvlm_video_generate \\
  --model mlx-community/SmolVLM2-500M-Video-Instruct-mlx \\
  --system "Focus on goals, fouls, yellow/red cards, and key plays in this soccer match" \\
  --prompt "Identify the highlights from this soccer game" \\
  --video soccer_match.mp4

# For General Highlights
python -m mlx_vlm.smolvlm_video_generate \\
  --model mlx-community/SmolVLM2-500M-Video-Instruct-mlx \\
  --system "Identify dramatic moments, scene changes, and important actions" \\
  --prompt "What are the key highlights?" \\
  --video long_video.mp4
```

### 2. **Python Transformers API**

```python
from transformers import AutoProcessor, AutoModelForImageTextToText
import torch

# Load model
processor = AutoProcessor.from_pretrained("HuggingFaceTB/SmolVLM2-2.2B-Instruct")
model = AutoModelForImageTextToText.from_pretrained(
    "HuggingFaceTB/SmolVLM2-2.2B-Instruct",
    torch_dtype=torch.float32,  # Use float32 for MPS
    device_map=None,
).to("mps")  # or "cuda" or "cpu"

# Process video
messages = [
    {
        "role": "user",
        "content": [
            {"type": "video", "path": "your_video.mp4"},
            {"type": "text", "text": "What are the key highlights in this video?"}
        ]
    },
]

inputs = processor.apply_chat_template(messages, return_tensors="pt")
inputs = {k: v.to("mps") for k, v in inputs.items()}

with torch.no_grad():
    generated_ids = model.generate(**inputs, max_new_tokens=200)

response = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
```

### 3. **Our Custom Highlight Generator**

```bash
# Process long videos with automatic segmentation and highlight detection
python video_highlight_generator.py

# Or customize in Python:
from video_highlight_generator import SmolVLMHighlightGenerator

generator = SmolVLMHighlightGenerator()
results = generator.generate_highlights(
    video_path="long_video.mp4",
    min_significance=6,  # Only highlights scored 6/10 or higher
    max_highlights=10    # Maximum 10 highlights
)
```

## 📋 System Prompt Recommendations

Based on HuggingFace documentation and testing, system prompts are crucial for directing SmolVLM2's focus:

### For Highlight Detection:
```
"Focus only on describing the key dramatic action or notable event occurring in this video segment. Skip general context or scene-setting details unless they are crucial to understanding the main action."
```

### For Sports Analysis:
```
"Analyze this sports video focusing on: goals, significant plays, fouls, cards, substitutions, and crowd reactions. Rate the importance of each moment from 1-10."
```

### For Scene Summarization:
```
"Provide a concise summary of the main events in this video. Focus on: character actions, scene transitions, important dialogue, and key plot points."
```

### For Technical Analysis:
```
"Describe the technical aspects of this video including: camera movements, lighting changes, special effects, and production techniques."
```

## 🎬 Video Processing Best Practices

### 1. **Video Preparation**
- **Format**: MP4 works best
- **Resolution**: No specific limits, but higher resolution = more processing time
- **Duration**: 
  - Short clips (< 30s): Direct processing
  - Long videos (> 1 minute): Use segmentation
  - Very long videos (> 1 hour): Use our highlight generator

### 2. **Segmentation Strategy**
For long videos, break them into segments:
- **Segment length**: 20-60 seconds optimal
- **Overlap**: 5-10 seconds between segments
- **Processing**: Analyze each segment independently
- **Aggregation**: Combine results and rank by significance

### 3. **Performance Optimization**
- **MLX** (Apple Silicon): ~2GB memory, fastest inference
- **CUDA** (NVIDIA): Good performance with bfloat16
- **MPS** (Apple Silicon): Use float32, moderate speed
- **CPU**: Slowest but works everywhere

## 📊 Output Examples

### Simple Analysis:
```
Input: 30-second sports clip
Output: "The video shows a soccer player dribbling past two defenders before scoring a goal in the bottom right corner. The crowd celebrates as the player raises his arms in victory."
Significance: 8/10
```

### Highlight Summary:
```json
{
  "highlights": [
    {
      "timestamp": "2:15-2:45",
      "description": "Goal scored with spectacular bicycle kick",
      "significance": 9
    },
    {
      "timestamp": "15:30-16:00", 
      "description": "Red card issued after hard tackle",
      "significance": 7
    }
  ]
}
```

## 🔧 Troubleshooting

### Common Issues:
1. **Video format not supported**: Convert to MP4 using ffmpeg
2. **Memory errors**: Use smaller models (500M instead of 2.2B)
3. **Long processing times**: Break video into smaller segments
4. **Poor quality analysis**: Adjust system prompts to be more specific

### Performance Tips:
- Use MLX on Apple Silicon for best performance
- Process videos in segments for better accuracy
- Use specific system prompts for your use case
- Consider video quality vs processing time trade-offs

## 📁 Available Scripts

1. **`video_highlight_generator.py`** - Automated highlight extraction
2. **`test_video_transformers.py`** - Transformers video analysis
3. **`mlx_examples.py`** - MLX command-line examples
4. **`create_test_video.py`** - Generate test videos

## 🚀 Next Steps

1. **Test with your videos**: Start with short clips to understand capabilities
2. **Experiment with system prompts**: Tailor prompts to your specific needs  
3. **Build custom workflows**: Combine with other tools for complete pipelines
4. **Scale up**: Process longer videos using segmentation approach

The SmolVLM2 video processing capabilities are powerful and versatile - perfect for content analysis, highlight generation, and automated video understanding!