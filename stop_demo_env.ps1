$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RuntimeDir = Join-Path $ProjectRoot "tmp\run-control"
$StatePath = Join-Path $RuntimeDir "demo-runtime.json"
$DockerExe = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
$FallbackJuiceShopName = "devsecops-juice-shop-3100"

function Write-Step {
  param([string]$Message)
  Write-Host "[STOP] $Message" -ForegroundColor Cyan
}

function Write-Ok {
  param([string]$Message)
  Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-WarnLine {
  param([string]$Message)
  Write-Host "[WARN] $Message" -ForegroundColor Yellow
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

function Load-State {
  if (-not (Test-Path $StatePath)) {
    return $null
  }
  return Get-Content -Raw -Path $StatePath | ConvertFrom-Json
}

$state = Load-State

if ($state -and $state.processes) {
  foreach ($proc in $state.processes) {
    if (Test-ProcessAlive -ProcessId ([int]$proc.pid)) {
      Write-Step "Stopping $($proc.name) (PID=$($proc.pid))"
      try {
        Stop-Process -Id ([int]$proc.pid) -Force -ErrorAction Stop
        Write-Ok "$($proc.name) stopped"
      } catch {
        Write-WarnLine "Failed to stop $($proc.name): $($_.Exception.Message)"
      }
    } else {
      Write-WarnLine "$($proc.name) is already stopped"
    }
  }

  Remove-Item -Path $StatePath -Force -ErrorAction SilentlyContinue
  Write-Ok "State file removed"
} else {
  Write-WarnLine "State file not found. Skipping managed process shutdown."
}

if (Test-Path $DockerExe) {
  $shouldRemoveFallback = $false
  if ($state -and $state.docker -and $state.docker.juice_mode -eq "docker-run") {
    $shouldRemoveFallback = $true
  }

  if ($shouldRemoveFallback) {
    Write-Step "Removing fallback Juice Shop container if it exists"
    & $DockerExe rm -f $FallbackJuiceShopName | Out-Null
  }

  Write-Step "Stopping Docker services"
  & $DockerExe compose down | Out-Host
  if ($LASTEXITCODE -ne 0) {
    throw "docker compose down failed"
  }
  Write-Ok "Docker services stopped"
} else {
  Write-WarnLine "Docker executable not found. Stop containers manually if needed."
}
