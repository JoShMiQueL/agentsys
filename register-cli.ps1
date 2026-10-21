# register-cli.ps1 — adds <repo>\bin to user PATH so `agentsys` works globally
$bin = Join-Path $PSScriptRoot 'bin'
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($userPath -split ';' -contains $bin) {
  Write-Host "agentsys already on PATH"
} else {
  [Environment]::SetEnvironmentVariable('Path', "$userPath;$bin", 'User')
  Write-Host "added $bin to user PATH — open a NEW terminal for `agentsys`"
}
