#!/bin/bash

# AWARE Keyboard Viewer - Quick Start Script

echo "🚀 Starting AWARE Keyboard Viewer..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install/update dependencies
echo "📚 Installing dependencies..."
pip install -q -r requirements.txt

# Create data directories if they don't exist
mkdir -p data/uploads data/filtered

# Run the Flask app
echo "✅ Starting Flask server..."
echo ""
echo "🌐 Open your browser and navigate to: http://localhost:8080"
echo "   or http://127.0.0.1:8080"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python app.py
