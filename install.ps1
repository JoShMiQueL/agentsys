# install.ps1 — install agent systems from systems/<name>/
# Usage:
#   .\install.ps1                        # reversing only (default)
#   .\install.ps1 -Systems reversing,devin
#   .\install.ps1 -Systems devin -SkipModels
param(
  [string[]]$Systems = @('reversing'),
  [switch]$SkipModels
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Error "Python 3.11+ required (used by agentsys CLI + tools). Install from python.org and re-run."
  exit 1
}
if (-not (Get-Command ollama -ErrorAction SilentlyContinue) -and -not $SkipModels) {
  Write-Error "Ollama required for model aliases. Install ollama.com or use -SkipModels."
  exit 1
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
