#!/bin/bash

# ResumeForge Setup & Runner Script for Ubuntu/Linux
# This script sets up python venv, npm packages, and runs both servers concurrently.

# Exit immediately if any command fails
set -e

echo "========================================="
echo "   ResumeForge Setup & Runner (Ubuntu)   "
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

# 5. Launch Servers Concurrently
echo -e "\n[4/4] Launching servers concurrently..."

# Define clean-up function to kill both servers on exit
cleanup() {
    echo -e "\nStopping servers..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

# Trap SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

# Start Backend
echo "-> Starting backend FastAPI server at http://localhost:8000 (Logging to backend.log)..."
backend/.venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8000 --app-dir backend > backend.log 2>&1 &
BACKEND_PID=$!

# Start Frontend
echo "-> Starting frontend Vite server at http://localhost:5173 (Logging to frontend.log)..."
(cd frontend && npm run dev) > frontend.log 2>&1 &
FRONTEND_PID=$!

echo -e "\nBoth servers are running in the background!"
echo "- Backend log: tail -f backend.log"
echo "- Frontend log: tail -f frontend.log"
echo -e "\nPress [Ctrl+C] to stop both servers."

# Keep the script running to hold the trap
wait
