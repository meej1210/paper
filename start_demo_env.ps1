$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$RuntimeDir = Join-Path $ProjectRoot "tmp\run-control"
$LogDir = Join-Path $RuntimeDir "logs"
$StatePath = Join-Path $RuntimeDir "demo-runtime.json"

$PythonExe = "D:\anaconda\python.exe"
$DockerExe = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
$NodeExe = "D:\nodejs\node.exe"
$ViteEntry = Join-Path $FrontendDir "node_modules\vite\bin\vite.js"
$FallbackJuiceShopName = "devsecops-juice-shop-3100"

function Write-Step {
  param([string]$Message)
  Write-Host "[START] $Message" -ForegroundColor Cyan
}

function Write-Ok {
  param([string]$Message)
  Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-WarnLine {
  param([string]$Message)
  Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Fail-Now {
  param([string]$Message)
  throw $Message
}

function Test-ProcessAlive {
  param([int]$ProcessId)
  try {
    Get-Process -Id $ProcessId -ErrorAction Stop | Out-Null
    return $true
  } catch {
    return $false
  }
}

function Stop-TrackedProcesses {
  param([array]$Processes)

  foreach ($proc in ($Processes | Where-Object { $_ -and $_.pid })) {
    if (Test-ProcessAlive -ProcessId ([int]$proc.pid)) {
      try {
        Stop-Process -Id ([int]$proc.pid) -Force -ErrorAction Stop
        Write-WarnLine "Stopped $($proc.name) (PID=$($proc.pid))"
      } catch {
        Write-WarnLine "Failed to stop $($proc.name): $($_.Exception.Message)"
      }
    }
  }
}

function Wait-HttpOk {
  param(
    [string]$Url,
    [int]$TimeoutSeconds = 60
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    try {
      $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
      if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
        return $true
      }
    } catch {
      Start-Sleep -Seconds 2
      continue
    }
    Start-Sleep -Seconds 1
  }
  return $false
}

function Wait-ForCondition {
  param(
    [scriptblock]$Check,
    [int]$TimeoutSeconds = 60,
    [int]$SleepSeconds = 2
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    try {
      if (& $Check) {
        return $true
      }
    } catch {
      # Ignore transient startup errors and keep polling until timeout.
    }
    Start-Sleep -Seconds $SleepSeconds
  }
  return $false
}

function Test-JuiceShopEndpoint {
  param([string]$Url)

  try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
    $content = [string]$response.Content
    return $content -match "(?i)juice"
  } catch {
    return $false
  }
}

function Test-BackendEndpoint {
  param([string]$Url)

  try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
    $content = [string]$response.Content
    return $content -match '"service"\s*:\s*"up"' -and $content -match '"database"\s*:\s*"up"'
  } catch {
    return $false
  }
}

function Test-FrontendEndpoint {
  param([string]$Url)

  try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
    $content = [string]$response.Content
    return $content -match "(?i)devsecops"
  } catch {
    return $false
  }
}

function Test-GenericHttpEndpoint {
  param([string]$Url)

  try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
    return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
  } catch {
    return $false
  }
}

function Test-PortAvailable {
  param([int]$Port)
  $pattern = "^\s*TCP\s+\S+:$Port\s+"
  $hits = netstat -ano -p TCP | Select-String -Pattern $pattern
  return @($hits).Count -eq 0
}

function Invoke-Docker {
  param([string[]]$Arguments)

  & $DockerExe @Arguments | Out-Host
  if ($LASTEXITCODE -ne 0) {
    Fail-Now ("docker command failed: " + ($Arguments -join " "))
  }
}

function Add-DastTarget {
  param(
    [array]$Targets,
    [string]$Name,
    [string]$Url,
    [string]$Kind
  )

  return @($Targets) + [pscustomobject]@{
    name = $Name
    url = $Url
    type = $Kind
  }
}

function Try-StartComposeLabTarget {
  param(
    [string]$Service,
    [string]$Name,
    [int]$Port,
    [string]$Url,
    [string]$Kind,
    [array]$Targets
  )

  if (Test-PortAvailable -Port $Port) {
    Write-Step "Starting $Name on port $Port via docker compose"
    try {
      Invoke-Docker -Arguments @("compose", "up", "-d", $Service)
      Write-Ok "$Name container command completed"
      return Add-DastTarget -Targets $Targets -Name $Name -Url $Url -Kind $Kind
    } catch {
      Write-WarnLine "Failed to start ${Name}: $($_.Exception.Message)"
      return $Targets
    }
  }

  if (Test-GenericHttpEndpoint -Url $Url) {
    Write-WarnLine "Port $Port is busy, but $Name is reachable there. Reusing it."
    return Add-DastTarget -Targets $Targets -Name $Name -Url $Url -Kind $Kind
  }

  Write-WarnLine "Port $Port is busy and $Name is not reachable. Skipping this DAST lab target."
  return $Targets
}

function Ensure-CommandPaths {
  if (-not (Test-Path $PythonExe)) {
    Fail-Now "Python not found: $PythonExe"
  }
  if (-not (Test-Path $DockerExe)) {
    Fail-Now "Docker not found: $DockerExe"
  }
  if (-not (Test-Path $NodeExe)) {
    Fail-Now "Node not found: $NodeExe"
  }
  if (-not (Test-Path $ViteEntry)) {
    Fail-Now "Vite entry not found: $ViteEntry. Run npm install in frontend first."
  }
}

function Load-State {
  if (-not (Test-Path $StatePath)) {
    return $null
  }
  return Get-Content -Raw -Path $StatePath | ConvertFrom-Json
}

function Save-State {
  param([hashtable]$State)
  $State | ConvertTo-Json -Depth 5 | Set-Content -Path $StatePath -Encoding UTF8
}

Ensure-CommandPaths
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

$existingState = Load-State
if ($existingState -and $existingState.processes) {
  $aliveProcesses = @($existingState.processes | Where-Object { Test-ProcessAlive -Pid ([int]$_.pid) })
  if ($aliveProcesses.Count -gt 0) {
    $names = ($aliveProcesses | ForEach-Object { "$($_.name)(PID=$($_.pid))" }) -join ", "
    Fail-Now "Existing managed demo processes found: $names. Run .\stop_demo_env.ps1 first."
  }
  Remove-Item -Path $StatePath -Force -ErrorAction SilentlyContinue
}

$apiOutLog = Join-Path $LogDir "api.out.log"
$apiErrLog = Join-Path $LogDir "api.err.log"
$workerOutLog = Join-Path $LogDir "worker.out.log"
$workerErrLog = Join-Path $LogDir "worker.err.log"
$frontendOutLog = Join-Path $LogDir "frontend.out.log"
$frontendErrLog = Join-Path $LogDir "frontend.err.log"

$started = @()

try {
  $dastTarget = $null
  $dastTargets = @()
  $juiceContainerName = $null
  $juiceMode = $null

  if (Test-PortAvailable -Port 6379) {
    Write-Step "Starting Docker service: redis"
    Invoke-Docker -Arguments @("compose", "up", "-d", "redis")
    Write-Ok "Redis container command completed"
  } else {
    Write-WarnLine "Port 6379 is busy. Reusing the existing Redis endpoint on 127.0.0.1:6379."
  }

  if (Test-PortAvailable -Port 3000) {
    Write-Step "Starting Juice Shop on port 3000 via docker compose"
    Invoke-Docker -Arguments @("compose", "up", "-d", "juice-shop")
    $dastTarget = "http://127.0.0.1:3000"
    $juiceContainerName = "devsecops-juice-shop"
    $juiceMode = "compose"
  } elseif (Test-JuiceShopEndpoint -Url "http://127.0.0.1:3000") {
    Write-WarnLine "Port 3000 is busy, but an existing Juice Shop target is already reachable there. Reusing it."
    $dastTarget = "http://127.0.0.1:3000"
    $juiceContainerName = $null
    $juiceMode = "reuse-existing"
  } elseif (Test-PortAvailable -Port 3100) {
    Write-WarnLine "Port 3000 is busy. Falling back to port 3100 for Juice Shop."
    & $DockerExe rm -f $FallbackJuiceShopName | Out-Null
    Write-Step "Starting Juice Shop fallback container on port 3100"
    Invoke-Docker -Arguments @("run", "-d", "--name", $FallbackJuiceShopName, "-p", "3100:3000", "bkimminich/juice-shop:latest")
    $dastTarget = "http://127.0.0.1:3100"
    $juiceContainerName = $FallbackJuiceShopName
    $juiceMode = "docker-run"
  } elseif (Test-JuiceShopEndpoint -Url "http://127.0.0.1:3100") {
    Write-WarnLine "Port 3100 is busy, but an existing Juice Shop target is already reachable there. Reusing it."
    $dastTarget = "http://127.0.0.1:3100"
    $juiceContainerName = $null
    $juiceMode = "reuse-existing"
  } else {
    Fail-Now "Both port 3000 and 3100 are busy. Free one of them before startup."
  }
  $dastTargets = Add-DastTarget -Targets $dastTargets -Name "Juice Shop" -Url $dastTarget -Kind "modern-web"
  Write-Ok "Juice Shop target is $dastTarget"

  $dastTargets = Try-StartComposeLabTarget `
    -Service "dvwa" `
    -Name "DVWA" `
    -Port 3001 `
    -Url "http://127.0.0.1:3001" `
    -Kind "classic-web" `
    -Targets $dastTargets
  $dastTargets = Try-StartComposeLabTarget `
    -Service "webgoat" `
    -Name "WebGoat" `
    -Port 3002 `
    -Url "http://127.0.0.1:3002/WebGoat" `
    -Kind "training-web" `
    -Targets $dastTargets
  $dastTargets = Try-StartComposeLabTarget `
    -Service "mutillidae" `
    -Name "Mutillidae II" `
    -Port 3003 `
    -Url "http://127.0.0.1:3003" `
    -Kind "classic-web" `
    -Targets $dastTargets

  $env:CELERY_TASK_ALWAYS_EAGER = "false"

  if (Test-PortAvailable -Port 5000) {
    Write-Step "Starting backend API"
    $apiProc = Start-Process -FilePath $PythonExe `
      -ArgumentList "run.py" `
      -WorkingDirectory $BackendDir `
      -RedirectStandardOutput $apiOutLog `
      -RedirectStandardError $apiErrLog `
      -PassThru
    $started += [pscustomobject]@{
      name = "api"
      pid = $apiProc.Id
      stdout = $apiOutLog
      stderr = $apiErrLog
    }
    Start-Sleep -Seconds 2
    if (-not (Test-ProcessAlive -ProcessId $apiProc.Id)) {
      Fail-Now "Backend API exited right after start. Check $apiErrLog"
    }
    Write-Ok "Backend API running, PID=$($apiProc.Id)"
  } elseif (Test-BackendEndpoint -Url "http://127.0.0.1:5000/api/health") {
    Write-WarnLine "Port 5000 is busy, but a healthy backend is already running there. Reusing it."
  } else {
    Fail-Now "Port 5000 is busy and the backend health endpoint is not usable."
  }

  Write-Step "Starting Celery worker"
  $workerProc = Start-Process -FilePath $PythonExe `
    -ArgumentList "-m", "celery", "-A", "app.workers.celery_app.celery_app", "worker", "--loglevel=info", "--pool=solo" `
    -WorkingDirectory $BackendDir `
    -RedirectStandardOutput $workerOutLog `
    -RedirectStandardError $workerErrLog `
    -PassThru
  $started += [pscustomobject]@{
    name = "worker"
    pid = $workerProc.Id
    stdout = $workerOutLog
    stderr = $workerErrLog
  }
  Start-Sleep -Seconds 3
  if (-not (Test-ProcessAlive -ProcessId $workerProc.Id)) {
    Fail-Now "Celery worker exited right after start. Check $workerErrLog"
  }
  Write-Ok "Celery worker running, PID=$($workerProc.Id)"

  if (Test-PortAvailable -Port 5173) {
    Write-Step "Starting frontend Vite"
    $frontendProc = Start-Process -FilePath $NodeExe `
      -ArgumentList $ViteEntry, "--host", "127.0.0.1", "--port", "5173", "--strictPort" `
      -WorkingDirectory $FrontendDir `
      -RedirectStandardOutput $frontendOutLog `
      -RedirectStandardError $frontendErrLog `
      -PassThru
    $started += [pscustomobject]@{
      name = "frontend"
      pid = $frontendProc.Id
      stdout = $frontendOutLog
      stderr = $frontendErrLog
    }
    Start-Sleep -Seconds 3
    if (-not (Test-ProcessAlive -ProcessId $frontendProc.Id)) {
      Fail-Now "Frontend Vite exited right after start. Check $frontendErrLog"
    }
  Write-Ok "Frontend Vite running, PID=$($frontendProc.Id)"
  } elseif (Test-FrontendEndpoint -Url "http://127.0.0.1:5173") {
    Write-WarnLine "Port 5173 is busy, but the frontend is already reachable there. Reusing it."
  } else {
    Fail-Now "Port 5173 is busy and the frontend endpoint is not usable."
  }

  $state = @{
    started_at = (Get-Date).ToString("s")
    project_root = $ProjectRoot
    processes = @($started)
    urls = @{
      frontend = "http://127.0.0.1:5173"
      backend_health = "http://127.0.0.1:5000/api/health"
      dast_target = $dastTarget
      dast_targets = @($dastTargets)
    }
    docker = @{
      juice_mode = $juiceMode
      juice_container = $juiceContainerName
    }
  }
  Save-State -State $state

  Write-Step "Waiting for backend health endpoint"
  if (-not (Wait-ForCondition -TimeoutSeconds 60 -Check { Test-BackendEndpoint -Url "http://127.0.0.1:5000/api/health" })) {
    Fail-Now "Backend health check did not pass in time. Check $apiErrLog and $workerErrLog"
  }
  Write-Ok "Backend health check passed"

  Write-Step "Waiting for frontend page"
  if (-not (Wait-ForCondition -TimeoutSeconds 60 -Check { Test-FrontendEndpoint -Url "http://127.0.0.1:5173" })) {
    Fail-Now "Frontend did not become reachable in time. Check $frontendErrLog"
  }
  Write-Ok "Frontend page is reachable"

  Write-Host ""
  Write-Host "Demo environment is ready:" -ForegroundColor Green
  Write-Host "  Frontend: http://127.0.0.1:5173"
  Write-Host "  Backend health: http://127.0.0.1:5000/api/health"
  Write-Host "  DAST targets:"
  foreach ($target in $dastTargets) {
    Write-Host "    - $($target.name): $($target.url)"
  }
  Write-Host "  State file: $StatePath"
  Write-Host "  Log dir: $LogDir"
} catch {
  Write-WarnLine "Startup failed. Cleaning up managed processes."
  Stop-TrackedProcesses -Processes $started

  if (Test-Path $StatePath) {
    Remove-Item -Path $StatePath -Force -ErrorAction SilentlyContinue
  }

  try {
    if ($juiceMode -eq "docker-run") {
      & $DockerExe rm -f $FallbackJuiceShopName | Out-Null
    }
    & $DockerExe compose down | Out-Host
  } catch {
    Write-WarnLine "Failed to bring Docker services down. Run docker compose down manually."
  }

  throw
}
