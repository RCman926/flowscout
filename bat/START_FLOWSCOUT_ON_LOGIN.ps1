# Silent FlowScout start after Windows login / reboot.
# Idempotent: if :8000 is already listening, exits without touching it.
# No browser — open http://127.0.0.1:8000/ when you want the desk.

$ErrorActionPreference = "SilentlyContinue"
# This file lives in bat\ — project root is one level up.
$root = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path (Join-Path $root "zerodte_websocket_server.py"))) {
    $root = "C:\Users\ryan_\Desktop\StreamlitExcel"
}
Set-Location $root

$listening = netstat -ano | Select-String ":8000" | Select-String "LISTENING"
if ($listening) {
    exit 0
}

# Disk / AV / network settle after login — only when we still need to start
Start-Sleep -Seconds 20

$listening = netstat -ano | Select-String ":8000" | Select-String "LISTENING"
if ($listening) {
    exit 0
}

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
}
if (-not $py) {
    exit 1
}

if (-not $env:IBKR_ENABLED) { $env:IBKR_ENABLED = "0" }

Start-Process -FilePath $py `
    -ArgumentList "zerodte_websocket_server.py" `
    -WorkingDirectory $root `
    -WindowStyle Hidden
