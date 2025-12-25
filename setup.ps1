# Syndicate - Automated Setup Script (Windows PowerShell)
# Run with: .\setup.ps1
# Requires: Python 3.10-3.13 (3.14 not supported due to numba)
# Auto-installs Python 3.12 via winget if needed

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "   Syndicate - Automated Setup" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""

# Function to check if winget is available
function Test-Winget {
    try {
        $null = Get-Command winget -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

# Function to install Python 3.12 via winget
function Install-Python312 {
    Write-Host "      Installing Python 3.12 via winget..." -ForegroundColor Cyan
    try {
        winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -eq 0) {
            Write-Host "      Python 3.12 installed successfully." -ForegroundColor Green
            Write-Host "      NOTE: You may need to restart your terminal for PATH changes." -ForegroundColor Yellow
            # Refresh PATH for current session
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            return $true
        } else {
            Write-Host "      WARNING: winget install returned non-zero exit code." -ForegroundColor Yellow
            return $false
        }
    } catch {
        Write-Host "      ERROR: Failed to install Python via winget." -ForegroundColor Red
        return $false
    }
}

# Function to get the best Python command available (prefer 3.12)
function Get-PythonCommand {
    # First, try py launcher with 3.12
    try {
        $ver = py -3.12 --version 2>&1
        if ($ver -match "Python 3\.12") {
            return "py -3.12"
        }
    } catch {}

    # Try py launcher with 3.11
    try {
        $ver = py -3.11 --version 2>&1
        if ($ver -match "Python 3\.11") {
            return "py -3.11"
        }
    } catch {}

    # Try py launcher with 3.10
    try {
        $ver = py -3.10 --version 2>&1
        if ($ver -match "Python 3\.10") {
            return "py -3.10"
        }
    } catch {}

    # Try py launcher with 3.13
    try {
        $ver = py -3.13 --version 2>&1
        if ($ver -match "Python 3\.13") {
            return "py -3.13"
        }
    } catch {}

    # Try default python
    try {
        $ver = python --version 2>&1
        if ($ver -match "Python 3\.1[0-3]") {
            return "python"
        }
    } catch {}

    return $null
}

# Check Python installation and version
Write-Host "[1/8] Checking Python installation..." -ForegroundColor Cyan

$pythonCmd = Get-PythonCommand

if ($null -eq $pythonCmd) {
    Write-Host "      No compatible Python (3.10-3.13) found." -ForegroundColor Yellow

    # Try to auto-install Python 3.12
    if (Test-Winget) {
        Write-Host "      Attempting automatic installation..." -ForegroundColor Cyan
        if (Install-Python312) {
            # Retry finding Python after install
            Start-Sleep -Seconds 2
            $pythonCmd = Get-PythonCommand
            if ($null -eq $pythonCmd) {
                Write-Host "      Please restart your terminal and run this script again." -ForegroundColor Yellow
                exit 0
            }
        } else {
            Write-Host "      ERROR: Automatic installation failed." -ForegroundColor Red
            Write-Host "      Please install Python 3.12 manually:" -ForegroundColor Yellow
            Write-Host "        winget install Python.Python.3.12" -ForegroundColor Gray
            Write-Host "        OR download from: https://www.python.org/downloads/" -ForegroundColor Gray
            exit 1
        }
    } else {
        Write-Host "      ERROR: winget not available for automatic install." -ForegroundColor Red
        Write-Host "      Please install Python 3.12 manually:" -ForegroundColor Yellow
        Write-Host "        Download from: https://www.python.org/downloads/" -ForegroundColor Gray
        Write-Host "      After installing, run this script again." -ForegroundColor Yellow
        exit 1
    }
}

# Display Python version
$pythonVersion = Invoke-Expression "$pythonCmd --version" 2>&1
Write-Host "      Using: $pythonVersion ($pythonCmd)" -ForegroundColor Green

# Create virtual environment (prefer venv312 for numba support)
Write-Host "[2/8] Creating virtual environment..." -ForegroundColor Cyan
$venvDir = "venv312"
if (Test-Path $venvDir) {
    Write-Host "      Virtual environment '$venvDir' already exists. Skipping creation." -ForegroundColor Yellow
} else {
    # Also check for legacy .venv
    if (Test-Path ".venv") {
        Write-Host "      Found legacy .venv - recommend migrating to venv312 for numba support." -ForegroundColor Yellow
        $venvDir = ".venv"
    } else {
        Invoke-Expression "$pythonCmd -m venv $venvDir"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "      Created $venvDir successfully." -ForegroundColor Green
        } else {
            Write-Host "      ERROR: Failed to create virtual environment." -ForegroundColor Red
            exit 1
        }
    }
}

# Activate virtual environment
Write-Host "[3/8] Activating virtual environment..." -ForegroundColor Cyan
try {
    & ".\$venvDir\Scripts\Activate.ps1"
    Write-Host "      Activated $venvDir" -ForegroundColor Green
} catch {
    Write-Host "      ERROR: Failed to activate virtual environment." -ForegroundColor Red
    Write-Host "      Try running: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Yellow
    exit 1
}

# Upgrade pip first
Write-Host "[4/8] Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip --quiet
Write-Host "      pip upgraded" -ForegroundColor Green

# Install dependencies
Write-Host "[5/8] Installing production dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "      Installed requirements.txt" -ForegroundColor Green
} else {
    Write-Host "      WARNING: Some packages may have failed to install." -ForegroundColor Yellow
}

# Install dev dependencies (optional)
Write-Host "[6/8] Installing development dependencies..." -ForegroundColor Cyan
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

# Ollama setup and model downloads
Write-Host "[7/8] Checking Ollama setup..." -ForegroundColor Cyan
$ollamaCmd = $null
try {
    $ollamaCmd = Get-Command ollama -ErrorAction Stop
} catch {
    $ollamaCmd = $null
}

if ($null -ne $ollamaCmd) {
    Write-Host "      Ollama CLI detected ($($ollamaCmd.Source))." -ForegroundColor Green
    $ollamaModels = @("llama3.2")
    foreach ($model in $ollamaModels) {
        Write-Host "      Pulling Ollama model '$model'..." -ForegroundColor Gray
        ollama pull $model
        if ($LASTEXITCODE -eq 0) {
            Write-Host "      Ollama model '$model' ready." -ForegroundColor Green
        } else {
            Write-Host "      WARNING: Failed to pull '$model'. Start Ollama with 'ollama serve' and retry." -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "      Ollama CLI not found. Skipping Ollama model download." -ForegroundColor Yellow
    Write-Host "      Install Ollama from https://ollama.ai to enable the local provider." -ForegroundColor Gray
}

# GGUF downloads for llama.cpp fallback
Write-Host "[8/8] Downloading GGUF models..." -ForegroundColor Cyan

$ggufDir = "$env:USERPROFILE\.cache\gold_standard\models"
if (-not (Test-Path $ggufDir)) {
    New-Item -ItemType Directory -Path $ggufDir -Force | Out-Null
}

$ggufFile = "$ggufDir\mistral-7b-instruct-v0.2.Q4_K_M.gguf"
$ggufUrl = "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
$expectedSize = 4370000000  # ~4.37 GB

if (Test-Path $ggufFile) {
    $currentSize = (Get-Item $ggufFile).Length
    if ($currentSize -ge ($expectedSize * 0.95)) {
        Write-Host "      GGUF model already downloaded ($([math]::Round($currentSize/1GB, 2)) GB)" -ForegroundColor Green
    } else {
        Write-Host "      Incomplete GGUF detected ($([math]::Round($currentSize/1GB, 2)) GB / 4.37 GB)" -ForegroundColor Yellow
        Write-Host "      Resuming download via Python..." -ForegroundColor Gray
        python scripts/local_llm.py --download mistral-7b
    }
} else {
    Write-Host "      Downloading Mistral 7B GGUF (4.4 GB)..." -ForegroundColor Gray
    Write-Host "      This may take 10-30 minutes depending on connection." -ForegroundColor Gray
    python scripts/local_llm.py --download mistral-7b
    if ($LASTEXITCODE -eq 0) {
        Write-Host "      GGUF model downloaded successfully." -ForegroundColor Green
    } else {
        Write-Host "      WARNING: GGUF download may have failed. Re-run setup to retry." -ForegroundColor Yellow
        Write-Host "      Manual download: python scripts/local_llm.py --download mistral-7b" -ForegroundColor Gray
    }
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
Write-Host "  2. (Optional) Start Ollama service: ollama serve"
Write-Host "  3. Run: python run.py --mode daily --no-ai  (test without AI)"
Write-Host "  4. Run: python run.py  (daemon mode, runs every 4 hours)"
Write-Host "  5. Run: python gui.py  (GUI dashboard)"
Write-Host ""
Write-Host "Virtual environment '$venvDir' is now active." -ForegroundColor Green
Write-Host "To deactivate later, run: deactivate" -ForegroundColor Gray
Write-Host ""
