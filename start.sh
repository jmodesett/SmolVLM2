#!/bin/bash

# Railway deployment start script for SmolVLM2 Video Analysis API

echo "🚀 Starting SmolVLM2 Video Analysis API..."
echo "🔧 Environment: Railway"
echo "📁 Working directory: $(pwd)"

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Get port from Railway environment variable
export PORT=${PORT:-8000}

echo "🌐 Starting API server on port $PORT..."

# Start the FastAPI application
python app.py
