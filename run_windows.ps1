$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

Write-Host "`n=== Sovereign AI Workbench | Windows 11 ===" -ForegroundColor Cyan

# Check Python
$python = Get-Command py -ErrorAction SilentlyContinue
if ($python) {
    $pythonCmd = 'py'
    $pythonArgs = @('-3')
} else {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        throw 'Python 3.11+ was not found. Install it from https://www.python.org/downloads/windows/ and enable Add Python to PATH.'
    }
    $pythonCmd = 'python'
    $pythonArgs = @()
}

# Check Ollama installation
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    throw 'Ollama was not found. Install Ollama for Windows from https://ollama.com/download, then reopen PowerShell.'
}

# Create isolated Python environment
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    Write-Host 'Creating Python virtual environment...'
    & $pythonCmd @pythonArgs -m venv .venv
}
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$venvPip = Join-Path $PSScriptRoot '.venv\Scripts\pip.exe'

Write-Host 'Installing Python dependencies...'
& $venvPython -m pip install --upgrade pip
& $venvPip install -r requirements.txt

# Start Ollama only if its local API is not already responding.
$ollamaReady = $false
try {
    $null = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2
    $ollamaReady = $true
} catch { }

if (-not $ollamaReady) {
    Write-Host 'Starting local Ollama service...'
    $env:OLLAMA_MAX_LOADED_MODELS = '1'
    $env:OLLAMA_NUM_PARALLEL = '1'
    $env:OLLAMA_KEEP_ALIVE = '0'
    Start-Process -FilePath $ollama.Source -ArgumentList 'serve' -WindowStyle Hidden
    $deadline = (Get-Date).AddSeconds(45)
    do {
        Start-Sleep -Seconds 2
        try {
            $null = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2
            $ollamaReady = $true
        } catch { }
    } while (-not $ollamaReady -and (Get-Date) -lt $deadline)
}

if (-not $ollamaReady) {
    throw 'Ollama did not start. Open the Ollama app and retry this script.'
}

Write-Host 'Downloading compact text model (first run only)...' -ForegroundColor Yellow
& $ollama.Source pull qwen2.5:1.5b

Write-Host "`nChecking NVIDIA GPU visibility..." -ForegroundColor Cyan
$nvidiaSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nvidiaSmi) {
    & $nvidiaSmi.Source --query-gpu=name,memory.total,driver_version --format=csv
} else {
    Write-Warning 'nvidia-smi is unavailable. Update/install the NVIDIA laptop GPU driver. Ollama may run on CPU until the driver is fixed.'
}

Write-Host "`nLaunching Streamlit at http://127.0.0.1:8501" -ForegroundColor Green
& $venvPython -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
