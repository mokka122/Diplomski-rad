$ErrorActionPreference = "Continue"

$Root = "C:\Projects_monika\Diplomski-rad"

Write-Host ""
Write-Host "========================================"
Write-Host "         OCEANEYE DEVELOPMENT STOP"
Write-Host "========================================"
Write-Host ""


# ============================================================
# 1. STOP FASTAPI / UVICORN
# ============================================================

Write-Host "[1/3] Stopping FastAPI backend..."

$backendProcesses = Get-CimInstance Win32_Process |
Where-Object {
    $_.CommandLine -and (
        $_.CommandLine -like "*uvicorn app.main:app*" -or
        $_.CommandLine -like "*app.main:app*"
    )
}

foreach ($process in $backendProcesses) {

    try {

        Write-Host "Stopping backend PID $($process.ProcessId)..."

        Stop-Process `
            -Id $process.ProcessId `
            -Force `
            -ErrorAction SilentlyContinue

    }
    catch {
    }
}


# Also check whoever currently owns port 8000.

$port8000 = Get-NetTCPConnection `
    -LocalPort 8000 `
    -State Listen `
    -ErrorAction SilentlyContinue

foreach ($connection in $port8000) {

    try {

        Write-Host "Releasing port 8000 from PID $($connection.OwningProcess)..."

        Stop-Process `
            -Id $connection.OwningProcess `
            -Force `
            -ErrorAction SilentlyContinue

    }
    catch {
    }
}

Start-Sleep -Seconds 1

Write-Host "FastAPI stopped."
Write-Host ""


# ============================================================
# 2. STOP VITE / FRONTEND
# ============================================================

Write-Host "[2/3] Stopping Vue frontend..."

$frontendProcesses = Get-CimInstance Win32_Process |
Where-Object {
    $_.CommandLine -and (
        $_.CommandLine -like "*vite*" -or
        $_.CommandLine -like "*npm run dev*"
    )
}

foreach ($process in $frontendProcesses) {

    try {

        Write-Host "Stopping frontend PID $($process.ProcessId)..."

        Stop-Process `
            -Id $process.ProcessId `
            -Force `
            -ErrorAction SilentlyContinue

    }
    catch {
    }
}

Start-Sleep -Seconds 1

Write-Host "Frontend stopped."
Write-Host ""


# ============================================================
# 3. STOP DOCKER INFRASTRUCTURE
# ============================================================

Write-Host "[3/3] Stopping Docker infrastructure..."

Set-Location $Root

docker compose down

Write-Host ""
Write-Host "Docker services stopped."
Write-Host ""

Write-Host "========================================"
Write-Host "             OCEANEYE STOPPED"
Write-Host "========================================"
Write-Host ""