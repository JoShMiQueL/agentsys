# get.ps1 — remote bootstrap:  irm <raw-url>/get.ps1 | iex
# Downloads the repo, installs deps+models+config, registers `agentsys` on PATH.
param(
  [string[]]$Systems = @('reversing'),
  [switch]$Devin,      # shorthand: also install the devin system
  [string]$Dest = "$env:USERPROFILE\.agent-systems"
)
$ErrorActionPreference = 'Stop'
$repo = 'JoShMiQueL/agent-systems'

if ($Devin -and $Systems -notcontains 'devin') { $Systems += 'devin' }

if (Test-Path "$Dest\.git") {
  Write-Host "existing install — git pull" -ForegroundColor Cyan
  git -C $Dest pull --ff-only
} else {
  Write-Host "downloading $repo -> $Dest" -ForegroundColor Cyan
  $zip = "$env:TEMP\agent-systems.zip"
  Invoke-WebRequest "https://github.com/$repo/archive/refs/heads/master.zip" -OutFile $zip
  Expand-Archive $zip "$env:TEMP\agent-systems-x" -Force
  Move-Item "$env:TEMP\agent-systems-x\agent-systems-master" $Dest -Force
  Remove-Item $zip, "$env:TEMP\agent-systems-x" -Recurse -Force
}

powershell -ExecutionPolicy Bypass -File "$Dest\install.ps1" -Systems $Systems
powershell -ExecutionPolicy Bypass -File "$Dest\register-cli.ps1"
Write-Host "`nDone. Open a new terminal and run: agentsys doctor" -ForegroundColor Green
