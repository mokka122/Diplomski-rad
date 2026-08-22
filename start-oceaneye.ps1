$ErrorActionPreference = "Stop"

$Root = "C:\Projects_monika\Diplomski-rad"
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"

$RedisContainer = "oceaneye-redis"
$KafkaContainer = "oceaneye-kafka"
$ElasticsearchContainer = "oceaneye-elasticsearch"

Write-Host ""
Write-Host "========================================"
Write-Host "        OCEANEYE DEVELOPMENT START"
Write-Host "========================================"
Write-Host ""


# ============================================================
# HELPER
# ============================================================

function Wait-WithDots {
    param (
        [string]$Message,
        [int]$Seconds = 1
    )

    Write-Host -NoNewline "$Message"
    Start-Sleep -Seconds $Seconds
    Write-Host "."
}


# ============================================================
# 1. DOCKER INFRASTRUCTURE
# ============================================================

Write-Host "[1/4] Starting Docker infrastructure..."
Write-Host ""

Set-Location $Root

docker compose up -d

if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose failed to start."
}

Write-Host ""
Write-Host "Docker containers started."
Write-Host ""
Write-Host "Waiting for infrastructure to become healthy..."
Write-Host ""


# ============================================================
# REDIS READINESS
# ============================================================

Write-Host "Checking Redis..."

$RedisReady = $false

for ($i = 0; $i -lt 60; $i++) {

    try {

        $result = docker exec `
            $RedisContainer `
            redis-cli ping `
            2>$null

        if ($result -match "PONG") {

            $RedisReady = $true
            break
        }

    }
    catch {
    }

    Start-Sleep -Seconds 1
}

if (-not $RedisReady) {
    throw "Redis did not become ready within 60 seconds."
}

Write-Host "Redis is ready."


# ============================================================
# ELASTICSEARCH READINESS
# ============================================================

Write-Host "Checking Elasticsearch..."

$ElasticsearchReady = $false

for ($i = 0; $i -lt 90; $i++) {

    try {

        $response = Invoke-RestMethod `
            -Uri "http://127.0.0.1:9200" `
            -Method Get `
            -TimeoutSec 2

        if ($response.version.number) {

            $ElasticsearchReady = $true
            break
        }

    }
    catch {
    }

    Start-Sleep -Seconds 1
}

if (-not $ElasticsearchReady) {

    Write-Host ""
    docker logs --tail 50 $ElasticsearchContainer

    throw "Elasticsearch did not become ready within 90 seconds."
}

Write-Host "Elasticsearch is ready."


# ============================================================
# KAFKA READINESS
# ============================================================

Write-Host "Checking Kafka..."

$KafkaReady = $false

for ($i = 0; $i -lt 90; $i++) {

    try {

        docker exec `
            $KafkaContainer `
            /opt/kafka/bin/kafka-topics.sh `
            --bootstrap-server localhost:9092 `
            --list `
            *> $null

        if ($LASTEXITCODE -eq 0) {

            $KafkaReady = $true
            break
        }

    }
    catch {
    }

    Start-Sleep -Seconds 1
}

if (-not $KafkaReady) {

    Write-Host ""
    docker logs --tail 50 $KafkaContainer

    throw "Kafka did not become ready within 90 seconds."
}

Write-Host "Kafka broker is ready."


# ============================================================
# EXTRA KAFKA STABILIZATION
# ============================================================

Write-Host "Allowing Kafka group coordinator to stabilize..."

Start-Sleep -Seconds 5

Write-Host ""
Write-Host "All infrastructure services are ready."
Write-Host ""

# ============================================================
# APPLICATION PORT PRE-FLIGHT
# ============================================================

Write-Host "Checking application ports..."

$existingBackend = (
    Get-NetTCPConnection `
        -LocalPort 8000 `
        -State Listen `
        -ErrorAction SilentlyContinue
)

if ($existingBackend) {

    Write-Host ""
    Write-Host "ERROR: Port 8000 is already occupied."
    Write-Host ""

    $existingBackend |
        Select-Object `
            LocalAddress,
            LocalPort,
            State,
            OwningProcess

    Write-Host ""

    foreach ($connection in $existingBackend) {

        $processId = $connection.OwningProcess

        Get-CimInstance Win32_Process `
            -Filter "ProcessId=$processId" |
            Select-Object `
                ProcessId,
                ParentProcessId,
                Name,
                CommandLine
    }

    throw (
        "OceanEye cannot start because another process " +
        "is already listening on port 8000. " +
        "Run .\stop-oceaneye.ps1 first."
    )
}

Write-Host "Port 8000 is available."
Write-Host ""

# ============================================================
# 2. FASTAPI BACKEND
# ============================================================

Write-Host "[2/4] Starting FastAPI backend..."
Write-Host ""

$backendProcess = Start-Process `
    powershell `
    -ArgumentList @(
        "-NoExit",
        "-Command",
        "cd '$Backend'; .\venv\Scripts\Activate.ps1; uvicorn app.main:app --host 127.0.0.1 --port 8000"    ) `
    -PassThru

Write-Host "FastAPI process started."
Write-Host ""


# ============================================================
# 3. WAIT FOR FASTAPI
# ============================================================

Write-Host "[3/4] Waiting for OceanEye backend..."
Write-Host ""

$BackendReady = $false

for ($i = 0; $i -lt 60; $i++) {

    try {

        $response = Invoke-RestMethod `
            -Uri "http://127.0.0.1:8000/" `
            -Method Get `
            -TimeoutSec 2

        if ($response.message -eq "OceanEye API is running") {

            $BackendReady = $true
            break
        }

    }
    catch {
    }

    Start-Sleep -Seconds 1
}

if (-not $BackendReady) {

    Write-Host ""
    Write-Host "FastAPI did not become ready."
    Write-Host ""
    Write-Host "Check the separate backend PowerShell window for the actual error."
    Write-Host ""

    throw "FastAPI backend did not become ready within 60 seconds."
}

Write-Host "FastAPI backend is ready."
Write-Host ""


# ============================================================
# DATABASE HEALTH
# ============================================================

Write-Host "Checking MongoDB Atlas connection..."

try {

    $mongoHealth = Invoke-RestMethod `
        -Uri "http://127.0.0.1:8000/health" `
        -Method Get `
        -TimeoutSec 5

    if ($mongoHealth.status -eq "healthy") {

        Write-Host "MongoDB Atlas is connected."
    }

}
catch {

    Write-Warning "FastAPI is running, but MongoDB Atlas health check failed."
    Write-Warning "Check Atlas Network Access / IP whitelist."
}

Write-Host ""


# ============================================================
# REDIS HEALTH
# ============================================================

Write-Host "Checking Redis backend connection..."

try {

    $redisHealth = Invoke-RestMethod `
        -Uri "http://127.0.0.1:8000/health/redis" `
        -Method Get `
        -TimeoutSec 5

    if ($redisHealth.status -eq "healthy") {

        Write-Host "Redis backend connection is healthy."
    }

}
catch {

    Write-Warning "FastAPI is running, but Redis health check failed."
}

Write-Host ""


# ============================================================
# WAIT FOR LIVE PIPELINE
# ============================================================

Write-Host "Waiting for OceanEye live pipeline..."

$PipelineReady = $false

for ($i = 0; $i -lt 60; $i++) {

    try {

        $pipeline = Invoke-RestMethod `
            -Uri "http://127.0.0.1:8000/health/pipeline" `
            -TimeoutSec 2

        if ($pipeline.status -eq "running") {

            $PipelineReady = $true
            break
        }

    }
    catch {
    }

    Start-Sleep -Seconds 1
}

if ($PipelineReady) {

    Write-Host "OceanEye live pipeline is running."
}
else {

    Write-Warning "Backend is running, but pipeline health is not fully ready yet."
}

Write-Host ""


# ============================================================
# 4. FRONTEND
# ============================================================

Write-Host "[4/4] Starting Vue frontend..."
Write-Host ""

$frontendProcess = Start-Process `
    powershell `
    -ArgumentList @(
        "-NoExit",
        "-Command",
        "cd '$Frontend'; npm run dev"
    ) `
    -PassThru

Write-Host ""
Write-Host "========================================"
Write-Host "           OCEANEYE IS RUNNING"
Write-Host "========================================"
Write-Host ""
Write-Host "Frontend:"
Write-Host "http://localhost:5173"
Write-Host ""
Write-Host "Backend:"
Write-Host "http://127.0.0.1:8000"
Write-Host ""
Write-Host "Swagger:"
Write-Host "http://127.0.0.1:8000/docs"
Write-Host ""
Write-Host "Pipeline health:"
Write-Host "http://127.0.0.1:8000/health/pipeline"
Write-Host ""
Write-Host "Infrastructure:"
Write-Host "Redis          localhost:6379"
Write-Host "Kafka          localhost:9092"
Write-Host "Elasticsearch  localhost:9200"
Write-Host ""