param([string]$DemoDir = '')
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$pidFile = if ($DemoDir) { Join-Path ([System.IO.Path]::GetFullPath($DemoDir)) 'processes.json' } else { Join-Path $project 'data/preproject/demo/processes.json' }
if (-not (Test-Path -LiteralPath $pidFile)) { Write-Output '没有演示进程记录。'; exit 0 }
$state = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
foreach ($entry in @($state.backend, $state.frontend)) {
  $process = Get-Process -Id $entry.id -ErrorAction SilentlyContinue
  if ($process -and $process.StartTime.ToUniversalTime().Ticks -eq [long]$entry.started -and $process.Path -eq $entry.path) { Stop-Process -Id $process.Id -Force }
}
Remove-Item -LiteralPath $pidFile
Write-Output '演示服务已停止。'
