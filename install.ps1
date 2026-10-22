# install.ps1 - agent-systems installer (bun-style)
# Remote:  powershell -c "irm https://raw.githubusercontent.com/JoShMiQueL/agentsys/master/install.ps1 | iex"
# Local:   .\install.ps1 [-Systems a,b] [-SkipModels] [-NoDeps]
# Init:    .\install.ps1 -InitProject [path] [-Force]  (seed .opencode/ into a project)
param(
  [string[]]$Systems = @(),
  [switch]$SkipModels,
  [switch]$NoDeps,
  [switch]$All,
  [switch]$NonInteractive,
  [string]$InitProject,
  [switch]$Force,
  [string]$Dest = "$env:USERPROFILE\.agentsys"
)

$ErrorActionPreference = 'Stop'

# normalize -Systems: accept 'a,b', 'a','b', or bare string across -File/-Command/REPL
$Systems = @($Systems | ForEach-Object { "$_" -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })

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
  if ($InitProject) { $args2 += @('-InitProject', $InitProject) }
  if ($Force) { $args2 += '-Force' }
  $psExe = 'powershell'
  if (Get-Command pwsh -ErrorAction SilentlyContinue) { $psExe = 'pwsh' }
  & $psExe -ExecutionPolicy Bypass -File "$Dest\install.ps1" @args2
  & $psExe -ExecutionPolicy Bypass -File "$Dest\register-cli.ps1"
  Write-Host "`nDone. Open a new terminal: agentsys doctor" -ForegroundColor Green
  exit 0
}

$root = $PSScriptRoot

# --- per-project init: seed .opencode/ into a project (memory, specs, proposals) ---
if ($PSBoundParameters.ContainsKey('InitProject')) {
  $target = if ($InitProject) { $InitProject } else { (Get-Location).Path }
  $resolved = Resolve-Path -LiteralPath $target -ErrorAction SilentlyContinue
  if (-not $resolved) { Write-Error "InitProject path not found: $InitProject"; exit 1 }
  $target = $resolved.Path
  $src = Join-Path $root 'templates\opencode'
  if (-not (Test-Path $src)) { Write-Error "templates\opencode not found under $root"; exit 1 }
  $dst = Join-Path $target '.opencode'
  Write-Host "== agentsys init-project ==" -ForegroundColor Cyan
  Write-Host "seeding $src -> $dst" -ForegroundColor DarkGray
  $copied = 0; $skipped = 0
  Get-ChildItem $src -Recurse -File -Force | ForEach-Object {
    $rel = $_.FullName.Substring($src.Length).TrimStart('\','/')
    $d = Join-Path $dst $rel
    if ((Test-Path $d) -and -not $Force) {
      Write-Host "  [skip] $rel (exists; use -Force to overwrite)" -ForegroundColor DarkYellow
      $skipped++
    } else {
      $verb = if (Test-Path $d) { 'force' } else { 'copy' }
      New-Item -ItemType Directory -Force (Split-Path $d) | Out-Null
      Copy-Item $_.FullName $d -Force
      Write-Host "  [$verb] $rel" -ForegroundColor DarkGray
      $copied++
    }
  }
  Write-Host "`nDone. $copied file(s) copied, $skipped skipped." -ForegroundColor Green
  Write-Host "NOTE: skipped files were left untouched - your evolved .opencode/memory/" -ForegroundColor DarkGray
  Write-Host "      is never clobbered unless you pass -Force." -ForegroundColor DarkGray
  exit 0
}

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

Write-Host "`n== agentsys install ==" -ForegroundColor Cyan
Write-Host "[1/4] checking dependencies..." -ForegroundColor DarkGray

# --- system selection ---
$avail = @(Get-ChildItem (Join-Path $root 'systems') -Directory | Select-Object -Expand Name)
if ($All) { $Systems = $avail }
elseif (-not $Systems -or $Systems.Count -eq 0) {
  if ($NonInteractive) {
    $Systems = @('general')
  } else {
    # TUI: arrows move, space toggles, 'a' all, enter confirms, esc cancels
    $sel = @($avail | ForEach-Object { $_ -eq 'general' })   # general preselected (default system)
    $pos = 0
    $maxw = ($avail | Measure-Object -Maximum { $_.Length }).Maximum
    Write-Host "Select systems: up/down=move  space=toggle  a=all  enter=confirm  esc=cancel"
    for ($j = 0; $j -lt $avail.Count; $j++) {
      $m = if ($sel[$j]) { '[x]' } else { '[ ]' }
      Write-Host "    $m $($avail[$j].PadRight($maxw))"
    }
    $lines = $avail.Count
    :pick while ($true) {
      $k = [Console]::ReadKey($true)
      if ($k.Key -eq 'UpArrow')   { $pos = ($pos + $lines - 1) % $lines }
      elseif ($k.Key -eq 'DownArrow') { $pos = ($pos + 1) % $lines }
      elseif ($k.Key -eq 'Spacebar')  { $sel[$pos] = -not $sel[$pos] }
      elseif ($k.KeyChar -eq 'a')     { $all = -not ($sel -notcontains $false); for ($j=0;$j -lt $lines;$j++) { $sel[$j]=$all } }
      elseif ($k.Key -eq 'Enter')     { break pick }
      elseif ($k.Key -eq 'Escape')    { Write-Host "cancelled"; exit 0 }
      try { [Console]::SetCursorPosition(0, [Console]::CursorTop - $lines) } catch {}
      for ($j = 0; $j -lt $lines; $j++) {
        $mark = if ($sel[$j]) { '[x]' } else { '[ ]' }
        $ptr  = if ($j -eq $pos) { '>' } else { ' ' }
        Write-Host ("  {0} {1} {2}" -f $ptr, $mark, $avail[$j].PadRight($maxw))
      }
    }
    if (-not ($sel -contains $true)) { Write-Host "nothing selected - cancelled"; exit 0 }
    $Systems = @($avail | Where-Object { $sel[$avail.IndexOf($_)] })
  }
}
$Systems = @($Systems | Where-Object { $avail -contains $_ })
if (-not $Systems.Count) { Write-Error "no valid systems selected"; exit 1 }

Write-Host "[2/4] selected: $($Systems -join ', ')" -ForegroundColor DarkGray
Write-Host "[3/4] models + config merge..." -ForegroundColor DarkGray

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

# user overrides overlay merges last so it always wins over fragments
$overlay = Join-Path $cfgDir 'agentsys-overrides.json'
if (Test-Path $overlay) { $frags += $overlay }

Write-Host "[4/4] merging into opencode.json..." -ForegroundColor DarkGray
New-Item -ItemType Directory -Force $cfgDir | Out-Null
if ($frags.Count) {
  python -X utf8 "$root\merge_config.py" --config "$cfgDir\opencode.json" @frags
}

# sync repo plugins -> ~/.config/opencode/plugins (auto-discovered by OpenCode 2)
$srcPlugins = Join-Path $root 'plugins'
if (Test-Path $srcPlugins) {
  $dstPlugins = Join-Path $cfgDir 'plugins'
  foreach ($p in Get-ChildItem $srcPlugins -Directory) {
    $dst = Join-Path $dstPlugins $p.Name
    New-Item -ItemType Directory -Force $dst | Out-Null
    Copy-Item "$($p.FullName)\*" $dst -Recurse -Force
    Write-Host "  [plugin] $($p.Name) -> $dst" -ForegroundColor DarkGray
  }
}

# global SDD skills -> ~/.config/opencode/skills (auto-discovered by OpenCode 2)
$srcSkills = Join-Path $root '.opencode\skills'
if (Test-Path $srcSkills) {
  $dstSkills = Join-Path $cfgDir 'skills'
  foreach ($s in Get-ChildItem $srcSkills -Directory) {
    $dst = Join-Path $dstSkills $s.Name
    New-Item -ItemType Directory -Force $dst | Out-Null
    Copy-Item "$($s.FullName)\*" $dst -Recurse -Force
    Write-Host "  [skill] $($s.Name) -> $dst" -ForegroundColor DarkGray
  }
}

# global commands -> ~/.config/opencode/commands
$srcCmds = Join-Path $root '.opencode\commands'
if (Test-Path $srcCmds) {
  $dstCmds = Join-Path $cfgDir 'commands'
  New-Item -ItemType Directory -Force $dstCmds | Out-Null
  foreach ($c in Get-ChildItem $srcCmds -File) {
    Copy-Item $c.FullName $dstCmds -Force
    Write-Host "  [command] $($c.Name) -> $dstCmds" -ForegroundColor DarkGray
  }
}

Write-Host "`nInstalled systems: $($Systems -join ', ')" -ForegroundColor Green
Write-Host "opencode.json backup: $cfgDir\opencode.json.bak-<ts>.json"
