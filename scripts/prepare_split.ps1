# prepare_split.ps1
$ErrorActionPreference = "Stop"

$root = "e:\CSOS"
$dest = "$root\prepared-split"
$backendDest = "$dest\backend"
$frontendDest = "$dest\frontend"

Write-Host "Creating directories..."
New-Item -ItemType Directory -Force -Path $backendDest | Out-Null
New-Item -ItemType Directory -Force -Path $frontendDest | Out-Null

# --- BACKEND MIGRATION ---
Write-Host "Copying Backend files..."
# Copy backend contents to root of new backend repo
Copy-Item -Path "$root\backend\*" -Destination $backendDest -Recurse -Force

Write-Host "Copying Engine files..."
# Copy engine to engine/ in new backend repo
$engineDest = "$backendDest\engine"
New-Item -ItemType Directory -Force -Path $engineDest | Out-Null
Copy-Item -Path "$root\engine\*" -Destination $engineDest -Recurse -Force

# --- FRONTEND MIGRATION ---
Write-Host "Copying Frontend files..."
# Copy frontend contents to root of new frontend repo
Copy-Item -Path "$root\frontend\*" -Destination $frontendDest -Recurse -Force

Write-Host "Done! Files are in $dest"
