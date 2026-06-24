param(
  [switch]$NoTunnel,
  [switch]$DryRun,
  [int]$LocalRedisPort = 6379,
  [string]$WorkerId = "os-worker-tongct-pc",
  [int]$ReviewTimeoutSeconds = 1800
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$AgentDir = Join-Path $RepoRoot "webreel-ai-agent"
$PythonExe = Join-Path $AgentDir "venv\Scripts\python.exe"
$SshKey = Join-Path $RepoRoot "key\ssh-key-2026-06-09.key"
$VpsHost = "161.118.200.184"
$VpsUser = "ubuntu"
$VpsTarget = "$VpsUser@$VpsHost"
$RemoteAppDir = "/home/ubuntu/webreel/webreel-ai-agent"

function Test-RequiredPath {
  param(
    [string]$Path,
    [string]$Label
  )

  if (-not (Test-Path -LiteralPath $Path)) {
    throw "$Label not found: $Path"
  }
}

function Test-LocalPortOpen {
  param([int]$Port)

  $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1

  return $null -ne $connection
}

function Get-VpsEnv {
  $envLines = ssh -i $SshKey $VpsTarget "cd $RemoteAppDir && grep -E '^(REDIS_PASSWORD|INTERNAL_API_KEY|GEMINI_MODEL)=' .env"
  $config = @{}

  foreach ($line in $envLines) {
    $parts = $line -split "=", 2
    if ($parts.Count -eq 2) {
      $config[$parts[0]] = $parts[1]
    }
  }

  foreach ($required in @("REDIS_PASSWORD", "INTERNAL_API_KEY", "GEMINI_MODEL")) {
    if (-not $config.ContainsKey($required) -or [string]::IsNullOrWhiteSpace($config[$required])) {
      throw "Missing $required from VPS .env"
    }
  }

  return $config
}

function Start-RedisTunnel {
  if ($NoTunnel) {
    Write-Host "Skipping SSH tunnel because -NoTunnel was provided."
    return
  }

  if (Test-LocalPortOpen -Port $LocalRedisPort) {
    Write-Host "Local Redis tunnel port $LocalRedisPort is already listening."
    return
  }

  Write-Host "Starting SSH tunnel on localhost:$LocalRedisPort..."
  $sshArgs = @(
    "-i", $SshKey,
    "-N",
    "-L", "$LocalRedisPort`:127.0.0.1:6379",
    $VpsTarget
  )

  Start-Process -FilePath "ssh.exe" -ArgumentList $sshArgs -WindowStyle Hidden | Out-Null
  Start-Sleep -Seconds 3

  if (-not (Test-LocalPortOpen -Port $LocalRedisPort)) {
    throw "SSH tunnel did not open localhost:$LocalRedisPort"
  }
}

function Test-RedisConnection {
  $checkScript = @'
import os
import redis

r = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
print("ping", r.ping())
print("os-queue", r.llen("os-queue"))
'@

  $checkScript | & $PythonExe -
}

Test-RequiredPath -Path $AgentDir -Label "Agent directory"
Test-RequiredPath -Path $PythonExe -Label "Python virtualenv"
Test-RequiredPath -Path $SshKey -Label "SSH key"

Start-RedisTunnel

Write-Host "Reading production worker config from VPS..."
$config = Get-VpsEnv

$env:REDIS_URL = "redis://:$($config["REDIS_PASSWORD"])@localhost:$LocalRedisPort/0"
$env:USE_SSH_TUNNEL = "false"
$env:WORKER_QUEUE = "os-queue"
$env:WORKER_ID = $WorkerId
$env:IDLE_THRESHOLD = "0"
$env:API_URL = "https://app.stardust.id.vn"
$env:INTERNAL_API_KEY = $config["INTERNAL_API_KEY"]
$env:UPLOAD_ENABLED = "true"
$env:CLEANUP_AFTER_UPLOAD = "true"
$env:GEMINI_MODEL = $config["GEMINI_MODEL"]
$env:PYTHONIOENCODING = "utf-8"
$env:REVIEW_TIMEOUT_SECONDS = "$ReviewTimeoutSeconds"

Write-Host "Testing Redis connection..."
Test-RedisConnection

if ($DryRun) {
  Write-Host "Dry run complete. Worker was not started."
  exit 0
}

Write-Host "Starting OS worker..."
Push-Location $AgentDir
try {
  & $PythonExe -u -m worker.os_worker
}
finally {
  Pop-Location
}
