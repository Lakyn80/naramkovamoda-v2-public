param(
  [string]$Server = "lucky@89.221.214.140",
  [string]$RemoteProject = "/home/lucky/projects/naramkova-moda-modular",
  [string]$RemoteEnvFile = "/home/lucky/.env.production",
  [string]$LocalDir = "",
  [switch]$KeepHistory
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($LocalDir)) {
  $LocalDir = Join-Path $PSScriptRoot "backups"
}

New-Item -ItemType Directory -Force -Path $LocalDir | Out-Null

$latestName = "nmm-prod-latest.tgz"
$remoteTmp = "/tmp/$latestName"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"

$remoteScript = @"
set -euo pipefail
cd $RemoteProject
trap 'docker compose -f docker-compose.prod.yml --env-file $RemoteEnvFile start backend >/dev/null 2>&1 || true' EXIT
docker compose -f docker-compose.prod.yml --env-file $RemoteEnvFile stop backend
tar -czf $remoteTmp data/database.db static/uploads
docker compose -f docker-compose.prod.yml --env-file $RemoteEnvFile start backend
trap - EXIT
"@

ssh $Server $remoteScript
scp "${Server}:$remoteTmp" (Join-Path $LocalDir $latestName)
ssh $Server "rm -f $remoteTmp"

if ($KeepHistory) {
  Copy-Item (Join-Path $LocalDir $latestName) (Join-Path $LocalDir "nmm-prod-db-uploads-$stamp.tgz") -Force
}

Write-Host "OK backup:" (Join-Path $LocalDir $latestName)
if ($KeepHistory) {
  Write-Host "OK history copy:" (Join-Path $LocalDir "nmm-prod-db-uploads-$stamp.tgz")
}
