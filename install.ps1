# install.ps1 - agent-systems installer (bun-style)
# Remote:  powershell -c "irm https://raw.githubusercontent.com/JoShMiQueL/agentsys/master/install.ps1 | iex"
# Local:   .\install.ps1 [-Systems a,b] [-SkipModels] [-NoDeps]
param(
  [string[]]$Systems = @(),
  [switch]$SkipModels,
  [switch]$NoDeps,
  [switch]$All,
  [switch]$NonInteractive,
  [string]$Dest = "$env:USERPROFILE\.agentsys"
)

$ErrorActionPreference = 'Stop'

# --- bootstrap: running via irm (no local repo) -> fetch repo, re-run self ---
if (-not $PSScriptRoot -or -not (Test-Path (Join-Path $PSScriptRoot 'systems'))) {
  $repo = 'JoShMiQueL/agentsys'
  $tag = $null
  try { $tag = (Invoke-RestMethod "https://api.github.com/repos/$repo/tags")[0].name } catch {}
  $ref = 'master'
  if ($tag) { $ref = "refs/tags/$tag" }
  if (Test-Path $Dest) {
    Write-Host "existing install at $Dest - clean reinstall ($ref)" -ForegroundColor Cyan
    Remove-Item "$Dest\*" -Recurse -Force
  } else {
    Write-Host "downloading $repo @ $ref -> $Dest" -ForegroundColor Cyan
  }
  $zip = "$env:TEMP\agentsys.zip"
  Invoke-WebRequest "https://github.com/$repo/archive/$ref.zip" -OutFile $zip
  Expand-Archive $zip "$env:TEMP\agentsys-x" -Force
  $src = (Get-ChildItem "$env:TEMP\agentsys-x" -Directory | Select-Object -First 1).FullName
  New-Item -ItemType Directory -Force $Dest | Out-Null
  Copy-Item "$src\*" $Dest -Recurse -Force
  Remove-Item $zip, "$env:TEMP\agentsys-x" -Recurse -Force
  if ($tag) { Set-Content "$Dest\VERSION" $tag }
  $args2 = @()
  if ($Systems.Count) { $args2 += @('-Systems', ($Systems -join ',')) }
  if ($SkipModels) { $args2 += '-SkipModels' }
  if ($NoDeps) { $args2 += '-NoDeps' }
  if ($All) { $args2 += '-All' }
  if ($NonInteractive) { $args2 += '-NonInteractive' }
  $psExe = 'powershell'
  if (Get-Command pwsh -ErrorAction SilentlyContinue) { $psExe = 'pwsh' }
  & $psExe -ExecutionPolicy Bypass -File "$Dest\install.ps1" @args2
  & $psExe -ExecutionPolicy Bypass -File "$Dest\register-cli.ps1"
  Write-Host "`nDone. Open a new terminal: agentsys doctor" -ForegroundColor Green
  exit 0
}

$root = $PSScriptRoot

function Ensure-Dep($cmd, $wingetId, $name) {
  if (Get-Command $cmd -ErrorAction SilentlyContinue) { return $true }
  if ($NoDeps) { Write-Error "$name missing (install $wingetId or drop -NoDeps)"; exit 1 }
  Write-Host "  [dep] $name missing - winget install $wingetId" -ForegroundColor Yellow
  winget install --id $wingetId -e --accept-source-agreements --accept-package-agreements -h
  $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
  if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
    Write-Error "$name installed but not on PATH yet - open a new terminal and re-run"
    exit 1
  }
}

Ensure-Dep python 'Python.Python.3.11' 'Python'
if (-not $SkipModels) { Ensure-Dep ollama 'Ollama.Ollama' 'Ollama' }
if (-not (Get-Command opencode2 -ErrorAction SilentlyContinue)) {
  Ensure-Dep npm 'OpenJS.NodeJS.LTS' 'Node.js'
  Write-Host "  [dep] opencode2 missing - npm i -g @opencode-ai/cli@next" -ForegroundColor Yellow
  npm i -g '@opencode-ai/cli@next'
}
$cfgDir = "$env:USERPROFILE\.config\opencode"

Write-Host "== agent-systems install ==" -ForegroundColor Cyan

# --- system selection ---
$avail = @(Get-ChildItem (Join-Path $root 'systems') -Directory | Select-Object -Expand Name)
if ($All) { $Systems = $avail }
elseif (-not $Systems -or $Systems.Count -eq 0) {
  if ($NonInteractive) {
    $Systems = @('reversing')
  } else {
    Write-Host "Available systems:"
    $map = @{}
    $i = 0
    foreach ($s in $avail) { $i++; $map[[string]$i] = $s; Write-Host "  $i) $s" }
    $pick = Read-Host "Select (e.g. 1,2 or 'all') [all]"
    if (-not $pick -or $pick -match '^(all|a)$') { $Systems = $avail }
    else { $Systems = @($pick -split ',' | ForEach-Object { $map[$_.Trim()] } | Where-Object { $_ }) }
  }
}
$Systems = @($Systems | Where-Object { $avail -contains $_ })
if (-not $Systems.Count) { Write-Error "no valid systems selected"; exit 1 }

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
