param([string]$Python = 'python', [int]$ApiPort = 8000, [int]$WebPort = 5173, [string]$DemoDir = '')
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$demoDir = if ($DemoDir) { [System.IO.Path]::GetFullPath($DemoDir) } else { Join-Path $project 'data/preproject/demo' }
$pidFile = Join-Path $demoDir 'processes.json'
if (Test-Path -LiteralPath $pidFile) { throw '已有演示进程记录。请先运行 scripts/stop_demo.ps1。' }
$pythonCmd = (Get-Command $Python -ErrorAction Stop).Source
$nodeCmd = (Get-Command node -ErrorAction Stop).Source
$vite = Join-Path $project 'frontend/node_modules/vite/bin/vite.js'
if (-not (Test-Path -LiteralPath $vite)) { throw '缺少前端依赖，请先在 frontend 运行 npm ci。' }
& $pythonCmd -c 'import fastapi, uvicorn, sqlalchemy, multipart, httpx' 2>$null
if ($LASTEXITCODE -ne 0) { throw '缺少后端依赖，请先安装 backend/requirements.txt。' }
try { & (Join-Path $PSScriptRoot 'init_baseline_env.ps1') -Python $pythonCmd } catch { Write-Warning '轻量训练环境尚未准备；数据治理仍可使用。请按资源说明准备独立依赖。' }
New-Item -ItemType Directory -Force -Path $demoDir | Out-Null
$env:AUTH_MODE = 'passwordless'
$env:APP_ENV = 'development'
$env:DEV_AUTH_USERNAME = 'admin'
$env:PLATFORM_DEMO_MODE = '1'
$env:DATABASE_URL = 'sqlite:///' + ((Join-Path $demoDir 'demo.db') -replace '\\','/')
$env:PREPROJECT_DATA_DIR = Join-Path $demoDir 'storage'
$env:VITE_API_PROXY_TARGET = "http://127.0.0.1:$ApiPort"
$backend = $null; $frontend = $null
try {
  $backend = Start-Process -FilePath $pythonCmd -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port',"$ApiPort") -WorkingDirectory (Join-Path $project 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $demoDir 'backend.out.log') -RedirectStandardError (Join-Path $demoDir 'backend.err.log')
  $frontend = Start-Process -FilePath $nodeCmd -ArgumentList @($vite,'--host','127.0.0.1','--port',"$WebPort",'--strictPort') -WorkingDirectory (Join-Path $project 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $demoDir 'frontend.out.log') -RedirectStandardError (Join-Path $demoDir 'frontend.err.log')
  @{ backend = @{ id=$backend.Id; started=$backend.StartTime.ToUniversalTime().Ticks; path=$backend.Path }; frontend = @{ id=$frontend.Id; started=$frontend.StartTime.ToUniversalTime().Ticks; path=$frontend.Path } } | ConvertTo-Json | Set-Content -LiteralPath $pidFile -Encoding UTF8
  $ready = $false
  for ($i=0; $i -lt 40; $i++) {
    try { & (Join-Path $PSScriptRoot 'smoke_test.ps1') -ApiPort $ApiPort -WebPort $WebPort -Quiet; $ready = $true; break } catch { Start-Sleep -Milliseconds 500 }
  }
  if (-not $ready) { throw '服务未就绪，请检查 data/preproject/demo 下的日志。' }
  $bootstrap = $null; $baselineReady = $false
  try {
    $bootstrap = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$ApiPort/api/preproject-data/examples/bootstrap" -TimeoutSec 90
    if (-not $bootstrap.ready -or -not $bootstrap.source.source_id -or -not $bootstrap.classification_version.version_id) { throw '默认示例或基础分类候选版本未准备完成。' }
    $baselineVersions = Invoke-RestMethod -Uri "http://127.0.0.1:$ApiPort/api/baseline/versions" -TimeoutSec 30
    if (-not ($baselineVersions.items | Where-Object { $_.version_id -eq $bootstrap.classification_version.version_id -and $_.is_default -and $_.compatible })) { throw '基础分类版本未通过训练输入验证。' }
    $demoStatus = Invoke-RestMethod -Uri "http://127.0.0.1:$ApiPort/api/preproject-data/examples/default" -TimeoutSec 30
    if (-not $demoStatus.ready -or $demoStatus.source.source_id -ne $bootstrap.source.source_id) { throw '默认治理示例验证失败。' }
    $baselineReady = $true
  } catch { Write-Warning "基础演示资源暂未就绪，平台仍可启动；请在训练页面选择准备基础训练数据并检查本机资源。原因：$($_.Exception.Message)" }
  Write-Output "前端：http://127.0.0.1:$WebPort/app/dashboard"
  Write-Output "后端：http://127.0.0.1:$ApiPort/health"
  Write-Output '首次访问请在登录页输入 admin，本地演示模式无需密码。'
  if ($baselineReady) { Write-Output '内置合成数据和治理模板已准备，基础分类候选版本已生成；不会自动启动训练。' }
} catch {
  if ($frontend -and -not $frontend.HasExited) { Stop-Process -Id $frontend.Id -Force }
  if ($backend -and -not $backend.HasExited) { Stop-Process -Id $backend.Id -Force }
  if (Test-Path -LiteralPath $pidFile) { Remove-Item -LiteralPath $pidFile }
  throw
}
