#!/bin/bash
# Quick start script for macOS/Linux

echo "========================================"
echo "Smart Fuel Financing Backend"
echo "Local Development Server"
echo "========================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo ""
    echo "WARNING: .env file not found!"
    echo "Please copy .env.example to .env and configure it."
    echo ""
    read -p "Press enter to continue anyway..."
fi

# Start server
echo ""
echo "Starting FastAPI server..."
echo "API Docs will be available at: http://localhost:8000/docs"
echo "Press Ctrl+C to stop the server"
echo ""
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

