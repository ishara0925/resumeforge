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

# Check .env file or GEMINI_API_KEY
$env_path = "backend/.env"
$key_exists = $false

if (Test-Path $env_path) {
    $content = Get-Content $env_path
    foreach ($line in $content) {
        if ($line -match "^GEMINI_API_KEY=(.+)$") {
            $val = $Matches[1].Trim()
            if ($val -and $val -ne "your_actual_key_here") {
                $key_exists = $true
            }
        }
    }
}

if (-not $key_exists) {
    Write-Host "`n[Setup] Gemini API Key Setup" -ForegroundColor Magenta
    Write-Host "ResumeForge requires a Gemini API Key to power its agents." -ForegroundColor Gray
    Write-Host "If you do not have one, get it from Google AI Studio: https://aistudio.google.com/" -ForegroundColor Gray
    
    $api_key = Read-Host "Please enter your Gemini API Key"
    $api_key = $api_key.Trim()
    
    if ($api_key) {
        "GEMINI_API_KEY=$api_key" | Out-File -FilePath $env_path -Encoding utf8
        Write-Host "Successfully saved GEMINI_API_KEY to $env_path" -ForegroundColor Green
    } else {
        Write-Host "No API key entered. You will need to manually set GEMINI_API_KEY in backend/.env before running." -ForegroundColor Yellow
        if (-not (Test-Path $env_path)) {
            "GEMINI_API_KEY=your_actual_key_here" | Out-File -FilePath $env_path -Encoding utf8
        }
    }
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
