param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("backend", "frontend", "admin", "frontend-admin")]
  [string]$Service,

  [string]$Tag = "",
  [switch]$SkipBuild,
  [string]$Server = "lucky@89.221.214.140",
  [string]$RemoteProject = "/home/lucky/projects/naramkova-moda-modular",
  [string]$RemoteEnvFile = "/home/lucky/.env.production"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Tag)) {
  $Tag = "v" + (Get-Date -Format "yyyy.MM.dd-HHmmss")
}

$serviceConfig = @{
  "backend" = @{
    Dockerfile = "docker/backend.Dockerfile"
    Image = "lakyn80/naramkova-backend"
    ComposeService = "backend"
    ContainerName = "nmm-backend"
  }
  "frontend" = @{
    Dockerfile = "docker/frontend.client.prod.Dockerfile"
    Image = "lakyn80/naramkova-frontend-client"
    ComposeService = "frontend"
    ContainerName = "nmm-frontend"
  }
  "admin" = @{
    Dockerfile = "docker/frontend.admin.prod.Dockerfile"
    Image = "lakyn80/naramkova-frontend-admin"
    ComposeService = "frontend-admin"
    ContainerName = "nmm-frontend-admin"
  }
  "frontend-admin" = @{
    Dockerfile = "docker/frontend.admin.prod.Dockerfile"
    Image = "lakyn80/naramkova-frontend-admin"
    ComposeService = "frontend-admin"
    ContainerName = "nmm-frontend-admin"
  }
}

$cfg = $serviceConfig[$Service]
$fullImage = "$($cfg.Image):$Tag"

Push-Location $PSScriptRoot
try {
  if (-not $SkipBuild) {
    Write-Host "Building $fullImage ..."
    docker build -f $cfg.Dockerfile -t $fullImage .
    if ($LASTEXITCODE -ne 0) { throw "Docker build failed." }

    Write-Host "Pushing $fullImage ..."
    docker push $fullImage
    if ($LASTEXITCODE -ne 0) { throw "Docker push failed." }
  } else {
    Write-Host "SkipBuild enabled. Deploying existing image tag: $fullImage"
  }

  $remoteScript = @"
set -euo pipefail
cd $RemoteProject
export TAG=$Tag
docker compose -f docker-compose.prod.yml --env-file $RemoteEnvFile pull $($cfg.ComposeService)
docker compose -f docker-compose.prod.yml --env-file $RemoteEnvFile up -d --no-deps --force-recreate $($cfg.ComposeService)
docker inspect $($cfg.ContainerName) --format '{{.Config.Image}} {{.State.Status}}'
"@

  Write-Host "Deploying $($cfg.ComposeService) on $Server ..."
  ssh $Server $remoteScript
  if ($LASTEXITCODE -ne 0) { throw "Remote deploy failed." }

  Write-Host ""
  Write-Host "OK deploy finished"
  Write-Host "Service: $($cfg.ComposeService)"
  Write-Host "Tag: $Tag"
  Write-Host "Image: $fullImage"
  Write-Host "DB: untouched"
}
finally {
  Pop-Location
}
