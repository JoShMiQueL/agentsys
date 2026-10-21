# install.ps1 — reproducible agent-env setup (idempotent)
# Usage:
#   .\install.ps1                    # full: models + reversing profile
#   .\install.ps1 -Devin             # also merge devin profile + plugin
#   .\install.ps1 -SkipModels        # only merge opencode config
param(
  [switch]$Devin,
  [switch]$SkipModels
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$cfgDir = "$env:USERPROFILE\.config\opencode"

Write-Host "== oblitebenchs install ==" -ForegroundColor Cyan

# --- 1. Ollama model aliases (baked num_ctx) ------------------------------
if (-not $SkipModels) {
  $models = @(
    @{ alias = 'glmflash-abl'; file = 'Modelfile.glmflash'; from = 'huihui_ai/glm-4.7-flash-abliterated:q4_K_S' },
    @{ alias = 'gptoss-abl';   file = 'Modelfile.gptoss';   from = 'huihui_ai/gpt-oss-abliterated:20b' },
    @{ alias = 'qwen38-abl';   file = 'Modelfile.qwen38';   from = 'huihui_ai/Qwen3.8-abliterated:27b' }
  )
  foreach ($m in $models) {
    $have = (ollama list 2>$null | Select-String "^$($m.alias):")
    if ($have) { Write-Host "  [skip] $($m.alias) exists" }
    else {
      $pulled = (ollama list 2>$null | Select-String ([regex]::Escape($m.from)))
      if (-not $pulled) { Write-Host "  [pull] $($m.from)"; ollama pull $m.from }
      Write-Host "  [create] $($m.alias) <- $($m.from)"
      ollama create $m.alias -f "$root\config\$($m.file)" | Out-Null
    }
  }
}

# --- 2. Merge opencode.json -------------------------------------------------
New-Item -ItemType Directory -Force $cfgDir | Out-Null
$frags = @("$root\config\profile_reversing.json")
if ($Devin) { $frags += "$root\config\profile_devin.json" }
python -X utf8 "$root\merge_config.py" --config "$cfgDir\opencode.json" @frags

# --- 3. Done ---------------------------------------------------------------
Write-Host "`nDone. Profiles merged: $($frags | ForEach-Object { Split-Path $_ -Leaf })" -ForegroundColor Green
Write-Host "Agents: orq(default) explorer coder analyst deep$(if ($Devin) { ' + dorq dexplore dcoder danalyst' })"
Write-Host "Backup of previous config: $cfgDir\opencode.json.bak-<ts>.json"
