param([int]$ApiPort = 8000, [int]$WebPort = 5173, [switch]$Quiet)
$ErrorActionPreference = 'Stop'
$api = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$ApiPort/health" -TimeoutSec 15
$web = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$WebPort/" -TimeoutSec 15
if ($api.StatusCode -ne 200 -or $web.StatusCode -ne 200 -or ($api.Content | ConvertFrom-Json).status -ne 'healthy') { throw '演示服务健康检查失败。' }
if (-not $Quiet) {
  $demo = Invoke-RestMethod -Uri "http://127.0.0.1:$ApiPort/api/preproject-data/examples/default" -TimeoutSec 15
  if (-not $demo.ready) { throw '服务在线，但默认示例尚未准备。' }
  Write-Output '后端、前端和默认示例检查通过。'
}
