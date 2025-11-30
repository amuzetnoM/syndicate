# Gold Standard - Automated Setup Script (Windows PowerShell)
# Run with: .\setup.ps1

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "   Gold Standard - Automated Setup" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""

# Check Python installation
Write-Host "[1/5] Checking Python installation..." -ForegroundColor Cyan
try {
    $pythonVersion = python --version 2>&1
    Write-Host "      Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "      ERROR: Python not found. Please install Python 3.11+ first." -ForegroundColor Red
    exit 1
}

# Create virtual environment
Write-Host "[2/5] Creating virtual environment..." -ForegroundColor Cyan
if (Test-Path ".venv") {
    Write-Host "      Virtual environment already exists. Skipping creation." -ForegroundColor Yellow
} else {
    python -m venv .venv
    if ($LASTEXITCODE -eq 0) {
        Write-Host "      Created .venv successfully." -ForegroundColor Green
    } else {
        Write-Host "      ERROR: Failed to create virtual environment." -ForegroundColor Red
        exit 1
    }
}

# Activate virtual environment
Write-Host "[3/5] Activating virtual environment..." -ForegroundColor Cyan
try {
    & .\.venv\Scripts\Activate.ps1
    Write-Host "      Activated .venv" -ForegroundColor Green
} catch {
    Write-Host "      ERROR: Failed to activate virtual environment." -ForegroundColor Red
    Write-Host "      Try running: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Yellow
    exit 1
}

# Install dependencies
Write-Host "[4/5] Installing production dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "      Installed requirements.txt" -ForegroundColor Green
} else {
    Write-Host "      WARNING: Some packages may have failed to install." -ForegroundColor Yellow
}

# Install dev dependencies (optional)
Write-Host "[5/5] Installing development dependencies..." -ForegroundColor Cyan
if (Test-Path "requirements-dev.txt") {
    pip install -r requirements-dev.txt --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host "      Installed requirements-dev.txt" -ForegroundColor Green
    } else {
        Write-Host "      WARNING: Some dev packages may have failed." -ForegroundColor Yellow
    }
} else {
    Write-Host "      Skipped (requirements-dev.txt not found)" -ForegroundColor Yellow
}

# Setup .env file
Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor Gray
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.template") {
        Copy-Item ".env.template" ".env"
        Write-Host "Created .env from template." -ForegroundColor Green
        Write-Host "IMPORTANT: Edit .env and add your GEMINI_API_KEY" -ForegroundColor Yellow
    }
} else {
    Write-Host ".env file already exists." -ForegroundColor Green
}

# Initialize Cortex memory
if (-not (Test-Path "cortex_memory.json")) {
    if (Test-Path "cortex_memory.template.json") {
        Copy-Item "cortex_memory.template.json" "cortex_memory.json"
        Write-Host "Initialized cortex_memory.json from template." -ForegroundColor Green
    }
} else {
    Write-Host "cortex_memory.json already exists." -ForegroundColor Green
}

# Create output directories
if (-not (Test-Path "output")) {
    New-Item -ItemType Directory -Path "output" | Out-Null
    New-Item -ItemType Directory -Path "output\charts" | Out-Null
    New-Item -ItemType Directory -Path "output\reports" | Out-Null
    New-Item -ItemType Directory -Path "output\reports\charts" | Out-Null
    Write-Host "Created output directories." -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "   Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Edit .env and add your GEMINI_API_KEY"
Write-Host "  2. Run: python run.py --mode daily --no-ai  (test without AI)"
Write-Host "  3. Run: python run.py  (interactive mode)"
Write-Host "  4. Run: python gui.py  (GUI dashboard)"
Write-Host ""
Write-Host "Virtual environment is now active." -ForegroundColor Green
Write-Host "To deactivate later, run: deactivate" -ForegroundColor Gray
Write-Host ""
