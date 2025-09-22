#!/usr/bin/env python3
"""
SmolVLM2 Test Script using Transformers
This script demonstrates how to use SmolVLM2 with the transformers library for image and video inference.
"""

import torch
from transformers import AutoProcessor, AutoModelForImageTextToText
from PIL import Image
import requests
import av
import numpy as np

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
        
        # Use float32 for MPS to avoid dtype issues, bfloat16 for CUDA
        if device == "mps":
            torch_dtype = torch.float32
        elif device == "cuda":
            torch_dtype = torch.bfloat16
        else:
            torch_dtype = torch.float32
        
        model = AutoModelForImageTextToText.from_pretrained(
            model_name,
            torch_dtype=torch_dtype,
            device_map="auto" if device == "cuda" else None,
        )
        
        if device in ["cpu", "mps"]:
            model = model.to(device)
        
        print(f"✅ Model loaded successfully on {device} with dtype {torch_dtype}")
        return model, processor, device
        
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return None, None, None

def test_image_inference(model, processor, device):
    """Test image understanding with SmolVLM2."""
    print("\n🖼️  Testing Image Inference...")
    
    try:
        # Load a sample image from the web
        image_url = "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/bee.jpg"
        image = Image.open(requests.get(image_url, stream=True).raw)
        
        # Prepare the conversation
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": "Can you describe this image in detail?"}
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
        ).to(device)
        
        # Generate response
        print("🔄 Generating response...")
        generated_ids = model.generate(**inputs, do_sample=False, max_new_tokens=150)
        generated_texts = processor.batch_decode(
            generated_ids,
            skip_special_tokens=True,
        )
        
        print("✅ Image inference successful!")
        print(f"Response: {generated_texts[0]}")
        
    except Exception as e:
        print(f"❌ Error in image inference: {e}")

def test_multi_image_inference(model, processor, device):
    """Test multi-image understanding with SmolVLM2."""
    print("\n🖼️🖼️  Testing Multi-Image Inference...")
    
    try:
        # Prepare the conversation with multiple images
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What are the differences between these two images?"},
                    {"type": "image", "url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/bee.jpg"},
                    {"type": "image", "url": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/0052a70beed5bf71b92610a43a52df6d286cd5f3/diffusers/rabbit.jpg"},
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
        ).to(device)
        
        # Generate response
        print("🔄 Generating response...")
        generated_ids = model.generate(**inputs, do_sample=False, max_new_tokens=150)
        generated_texts = processor.batch_decode(
            generated_ids,
            skip_special_tokens=True,
        )
        
        print("✅ Multi-image inference successful!")
        print(f"Response: {generated_texts[0]}")
        
    except Exception as e:
        print(f"❌ Error in multi-image inference: {e}")

def main():
    """Main function to run all tests."""
    print("🚀 SmolVLM2 Transformers Test Script")
    print("=" * 50)
    
    # Load model
    model, processor, device = load_model()
    
    if model is None:
        print("❌ Failed to load model. Exiting.")
        return
    
    # Test image inference
    test_image_inference(model, processor, device)
    
    # Test multi-image inference
    test_multi_image_inference(model, processor, device)
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()