param(
  [string]$Server = "lucky@89.221.214.140",
  [string]$RemoteProject = "/home/lucky/projects/naramkova-moda-modular",
  [string]$RemoteEnvFile = "/home/lucky/.env.production",
  [string]$BackupFile = "",
  [switch]$WithBackup
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($BackupFile)) {
  $BackupFile = Join-Path (Join-Path $PSScriptRoot "backups") "nmm-prod-latest.tgz"
}

if (-not (Test-Path $BackupFile)) {
  throw "Backup file not found: $BackupFile"
}

$remoteRestore = "/tmp/nmm-prod-restore.tgz"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"

scp $BackupFile "${Server}:$remoteRestore"

$backupCmd = ""
if ($WithBackup) {
  $backupCmd = "cp data/database.db data/database.db.pre-restore.$stamp.bak"
}

$remoteScript = @"
set -euo pipefail
cd $RemoteProject
$backupCmd
docker compose -f docker-compose.prod.yml --env-file $RemoteEnvFile stop backend frontend frontend-admin
tar -xzf $remoteRestore -C .
rm -f $remoteRestore
docker compose -f docker-compose.prod.yml --env-file $RemoteEnvFile up -d backend frontend frontend-admin
"@

ssh $Server $remoteScript

Write-Host "OK restored from:" $BackupFile
