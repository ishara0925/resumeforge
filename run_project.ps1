# ResumeForge Full-Stack Setup & Run Script
# Operating System: Windows (PowerShell)

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "     ResumeForge Setup & Runner Script    " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Check Python installation
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not in system PATH. Please install Python 3.10+ and try again."
    Exit
}

# 2. Check Node.js/npm installation
if (!(Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error "Node/npm is not installed or not in system PATH. Please install Node.js and try again."
    Exit
}

# 3. Setup Python Backend
Write-Host "`n[1/4] Setting up Python virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path "backend/.venv")) {
    Write-Host "Creating virtual environment in backend/.venv..." -ForegroundColor Gray
    Start-Process python -ArgumentList "-m venv backend/.venv" -Wait
} else {
    Write-Host "Virtual environment already exists." -ForegroundColor Gray
}

Write-Host "`n[2/4] Installing backend dependencies..." -ForegroundColor Yellow
# Run pip install inside the virtual environment
Start-Process "backend/.venv/Scripts/python.exe" -ArgumentList "-m pip install -r backend/requirements.txt" -Wait -NoNewWindow
Write-Host "Backend dependencies installed successfully." -ForegroundColor Gray

# Check .env file
if (-not (Test-Path "backend/.env")) {
    Write-Host "`n[Warning] backend/.env file not found. Creating a template..." -ForegroundColor Magenta
    New-Item -Path "backend/.env" -ItemType File -Value "GEMINI_API_KEY=your_actual_key_here`n" | Out-Null
    Write-Host "Template created at backend/.env. Please fill in your GEMINI_API_KEY before running the agents." -ForegroundColor Gray
}

# 4. Setup React Frontend
Write-Host "`n[3/4] Checking frontend dependencies..." -ForegroundColor Yellow
if (-not (Test-Path "frontend/node_modules")) {
    Write-Host "node_modules not found. Installing npm dependencies (this may take a minute)..." -ForegroundColor Gray
    # Run npm install inside frontend directory
    Start-Process cmd -ArgumentList "/c cd frontend && npm install" -Wait
    Write-Host "Frontend dependencies installed successfully." -ForegroundColor Gray
} else {
    Write-Host "Frontend dependencies already installed." -ForegroundColor Gray
}

# 5. Launch Servers
Write-Host "`n[4/4] Launching servers in concurrent windows..." -ForegroundColor Yellow

# Start FastAPI Backend in a new window
Write-Host "-> Launching backend FastAPI server at http://localhost:8000" -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .venv\Scripts\activate; python -m uvicorn app:app --reload --port 8000"

# Start Vite Frontend in a new window
Write-Host "-> Launching frontend Vite React server at http://localhost:5173" -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"

Write-Host "`nSetup and launching complete! Both servers are running in separate PowerShell windows." -ForegroundColor Cyan
Write-Host "Press Ctrl+C in their respective windows to stop them." -ForegroundColor Cyan
