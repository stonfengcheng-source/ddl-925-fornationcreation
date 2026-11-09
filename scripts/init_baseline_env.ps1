param([string]$Python = 'python', [switch]$InstallDependencies)
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$envDir = Join-Path $project 'data/runtime/baseline-env'
$pythonCmd = (Get-Command $Python -ErrorAction Stop).Source
$target = Join-Path $envDir 'Scripts/python.exe'
if (-not (Test-Path -LiteralPath $target)) {
  if ($InstallDependencies) { & $pythonCmd -m venv $envDir } else { & $pythonCmd -m venv --without-pip --system-site-packages $envDir }
  if ($LASTEXITCODE -ne 0) { throw '轻量训练环境创建失败。' }
}
if ($InstallDependencies) {
  & $target -m pip install -r (Join-Path $project 'configs/baseline-requirements.txt')
  if ($LASTEXITCODE -ne 0) { throw '轻量训练依赖安装失败。' }
}
& $target (Join-Path $project 'scripts/check_baseline_env.py')
if ($LASTEXITCODE -ne 0) { throw '轻量训练依赖尚未就绪：可在独立环境中使用 -InstallDependencies 安装。' }
Write-Output '轻量训练解释器和依赖已检查。'
