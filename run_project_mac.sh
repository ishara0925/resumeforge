#!/bin/bash

# ResumeForge Setup & Runner Script for macOS
# This script sets up python venv, npm packages, and spawns both servers in separate Terminal windows.

# Exit immediately if any command fails
set -e

echo "========================================="
echo "    ResumeForge Setup & Runner (macOS)   "
echo "========================================="

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed or not in PATH." >&2
    exit 1
fi

# 2. Check npm
if ! command -v npm &> /dev/null; then
    echo "Error: npm is not installed or not in PATH." >&2
    exit 1
fi

# 3. Setup Python Backend
echo -e "\n[1/4] Setting up Python virtual environment..."
if [ ! -d "backend/.venv" ]; then
    echo "Creating virtual environment in backend/.venv..."
    python3 -m venv backend/.venv
else
    echo "Virtual environment already exists."
fi

echo -e "\n[2/4] Installing backend dependencies..."
backend/.venv/bin/pip install -r backend/requirements.txt
echo "Backend dependencies installed successfully."

if [ ! -f "backend/.env" ]; then
    echo -e "\n[Warning] backend/.env file not found. Creating a template..."
    echo "GEMINI_API_KEY=your_actual_key_here" > backend/.env
    echo "Template created at backend/.env. Please fill in your GEMINI_API_KEY before running the agents."
fi

# 4. Setup React Frontend
echo -e "\n[3/4] Checking frontend dependencies..."
if [ ! -d "frontend/node_modules" ]; then
    echo "node_modules not found. Installing npm dependencies (this may take a minute)..."
    (cd frontend && npm install)
    echo "Frontend dependencies installed successfully."
else
    echo "Frontend dependencies already installed."
fi

# 5. Launch Servers
echo -e "\n[4/4] Launching servers in separate Terminal windows..."

# Absolute path to root
ROOT_DIR=$(pwd)

# Start FastAPI Backend in a new Terminal window via AppleScript
echo "-> Launching backend FastAPI server at http://localhost:8000"
osascript -e "tell application \"Terminal\" to do script \"cd '$ROOT_DIR/backend' && source .venv/bin/activate && python -m uvicorn app:app --reload --port 8000\""

# Start Vite Frontend in a new Terminal window via AppleScript
echo "-> Launching frontend Vite React server at http://localhost:5173"
osascript -e "tell application \"Terminal\" to do script \"cd '$ROOT_DIR/frontend' && npm run dev\""

echo -e "\nSetup and launching complete! Both servers are running in separate macOS Terminal windows."
