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

# Check .env file or GEMINI_API_KEY
ENV_PATH="backend/.env"
KEY_EXISTS=false

if [ -f "$ENV_PATH" ]; then
    if grep -qE "^GEMINI_API_KEY=[^[:space:]]+" "$ENV_PATH" && ! grep -q "your_actual_key_here" "$ENV_PATH"; then
        KEY_EXISTS=true
    fi
fi

if [ "$KEY_EXISTS" = false ]; then
    echo -e "\n[Setup] Gemini API Key Setup"
    echo "ResumeForge requires a Gemini API Key to power its agents."
    echo "Get your key from Google AI Studio: https://aistudio.google.com/"
    
    read -p "Please enter your Gemini API Key: " API_KEY
    API_KEY=$(echo "$API_KEY" | xargs)
    
    if [ -n "$API_KEY" ]; then
        echo "GEMINI_API_KEY=$API_KEY" > "$ENV_PATH"
        echo "Successfully saved GEMINI_API_KEY to $ENV_PATH"
    else
        echo "No API key entered. You will need to manually set GEMINI_API_KEY in backend/.env before running."
        if [ ! -f "$ENV_PATH" ]; then
            echo "GEMINI_API_KEY=your_actual_key_here" > "$ENV_PATH"
        fi
    fi
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
