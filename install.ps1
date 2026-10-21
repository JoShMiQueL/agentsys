# install.ps1 — agent-systems installer (bun-style)
# Remote:  powershell -c "irm https://raw.githubusercontent.com/JoShMiQueL/agentsys/master/install.ps1 | iex"
# Local:   .\install.ps1 [-Systems a,b] [-SkipModels] [-NoDeps]
param(
  [string[]]$Systems = @('reversing'),
  [switch]$SkipModels,
  [switch]$NoDeps,
  [string]$Dest = "$env:USERPROFILE\.agentsys"
)

$ErrorActionPreference = 'Stop'

# --- bootstrap: running via irm (no local repo) -> fetch repo, re-run self ---
if (-not $PSScriptRoot -or -not (Test-Path (Join-Path $PSScriptRoot 'systems'))) {
  $repo = 'JoShMiQueL/agentsys'
  if (Test-Path "$Dest\.git") {
    Write-Host "existing install at $Dest — git pull" -ForegroundColor Cyan
    git -C $Dest pull --ff-only
  } elseif (Get-Command git -ErrorAction SilentlyContinue) {
    Write-Host "cloning $repo -> $Dest" -ForegroundColor Cyan
    git clone --depth 1 "https://github.com/$repo.git" $Dest
    git -C $Dest fetch --tags -f 2>$null
  } else {
    Write-Host "downloading $repo -> $Dest (no git; snapshots can't git-update)" -ForegroundColor Cyan
    $zip = "$env:TEMP\agentsys.zip"
    Invoke-WebRequest "https://github.com/$repo/archive/refs/heads/master.zip" -OutFile $zip
    Expand-Archive $zip "$env:TEMP\agentsys-x" -Force
    Move-Item "$env:TEMP\agentsys-x\agentsys-master" $Dest -Force
    Remove-Item $zip, "$env:TEMP\agentsys-x" -Recurse -Force
  }
  # stamp installed version (latest tag)
  try {
    $tag = (Invoke-RestMethod "https://api.github.com/repos/$repo/tags")[0].name
    if ($tag) { Set-Content "$Dest\VERSION" $tag }
  } catch {}
  $args2 = @("-Systems", ($Systems -join ','))
  if ($SkipModels) { $args2 += '-SkipModels' }
  if ($NoDeps) { $args2 += '-NoDeps' }
  powershell -ExecutionPolicy Bypass -File "$Dest\install.ps1" @args2
  powershell -ExecutionPolicy Bypass -File "$Dest\register-cli.ps1"
  Write-Host "`nDone. Open a new terminal: agentsys doctor" -ForegroundColor Green
  exit 0
}

$root = $PSScriptRoot

function Ensure-Dep($cmd, $wingetId, $name) {
  if (Get-Command $cmd -ErrorAction SilentlyContinue) { return $true }
  if ($NoDeps) { Write-Error "$name missing (install $wingetId or drop -NoDeps)"; exit 1 }
  Write-Host "  [dep] $name missing — winget install $wingetId" -ForegroundColor Yellow
  winget install --id $wingetId -e --accept-source-agreements --accept-package-agreements -h
  $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
  if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
    Write-Error "$name installed but not on PATH yet — open a new terminal and re-run"
    exit 1
  }
}

Ensure-Dep python 'Python.Python.3.11' 'Python'
if (-not $SkipModels) { Ensure-Dep ollama 'Ollama.Ollama' 'Ollama' }
if (-not (Get-Command opencode2 -ErrorAction SilentlyContinue)) {
  Ensure-Dep npm 'OpenJS.NodeJS.LTS' 'Node.js'
  Write-Host "  [dep] opencode2 missing — npm i -g @opencode-ai/cli@next" -ForegroundColor Yellow
  npm i -g '@opencode-ai/cli@next'
}
$cfgDir = "$env:USERPROFILE\.config\opencode"

Write-Host "== agent-systems install ==" -ForegroundColor Cyan

$frags = @()
foreach ($sys in $Systems) {
  $sdir = Join-Path $root "systems\$sys"
  if (-not (Test-Path $sdir)) { Write-Warning "system '$sys' not found, skipping"; continue }

  # models declared by the system
  $mfile = Join-Path $sdir 'models.json'
  if ((Test-Path $mfile) -and -not $SkipModels) {
    $mj = Get-Content $mfile | ConvertFrom-Json
    foreach ($m in $mj.models) {
      if (ollama list 2>$null | Select-String "^$($m.alias):") {
        Write-Host "  [skip] $($m.alias) exists"
      } else {
        if (-not (ollama list 2>$null | Select-String ([regex]::Escape($m.pull)))) {
          Write-Host "  [pull] $($m.pull)"; ollama pull $m.pull
        }
        Write-Host "  [create] $($m.alias) <- $($m.pull)"
        ollama create $m.alias -f (Join-Path $sdir "models\$($m.file)") | Out-Null
      }
    }
  }

  $frag = Join-Path $sdir 'system.json'
  if (Test-Path $frag) { $frags += $frag }
}

New-Item -ItemType Directory -Force $cfgDir | Out-Null
if ($frags.Count) {
  python -X utf8 "$root\merge_config.py" --config "$cfgDir\opencode.json" @frags
}

Write-Host "`nInstalled systems: $($Systems -join ', ')" -ForegroundColor Green
Write-Host "opencode.json backup: $cfgDir\opencode.json.bak-<ts>.json"
