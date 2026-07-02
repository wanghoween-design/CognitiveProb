# ========================================
# AutoDL 上传脚本（Windows PowerShell）
# 用法：在本地执行 .\scripts\autodl_upload.ps1
# ========================================

$HOST = "connect.nmb1.seetacloud.com"
$PORT = "32175"
$USER = "root"
$REMOTE_DIR = "/root/Multi-Agent"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "CognitiveProbe AutoDL 上传脚本" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# ==================== 1. 打包项目代码 ====================
Write-Host "`n[1/4] 打包项目代码..." -ForegroundColor Yellow

$PROJECT_DIR = Split-Path $PSScriptRoot -Parent
$TEMP_DIR = "$env:TEMP\autodl_upload"
$ARCHIVE = "$TEMP_DIR\project.tar.gz"

# 创建临时目录
if (Test-Path $TEMP_DIR) { Remove-Item $TEMP_DIR -Recurse -Force }
New-Item -ItemType Directory -Path $TEMP_DIR -Force | Out-Null

# 打包（排除大文件）
Write-Host "正在打包..."
Push-Location $PROJECT_DIR
tar -czf $ARCHIVE --exclude="models" --exclude="adapters" --exclude=".venv" --exclude="__pycache__" --exclude=".git" --exclude="learning" --exclude="_docs" --exclude="CodeGuard" .
Pop-Location

$archiveSize = (Get-Item $ARCHIVE).Length / 1MB
Write-Host "✅ 打包完成: $([math]::Round($archiveSize, 2)) MB" -ForegroundColor Green

# ==================== 2. 上传项目代码 ====================
Write-Host "`n[2/4] 上传项目代码..." -ForegroundColor Yellow

scp -P $PORT $ARCHIVE "$USER@$HOST`:/$TEMP_DIR/"
Write-Host "✅ 项目代码上传完成" -ForegroundColor Green

# ==================== 3. 上传训练数据 ====================
Write-Host "`n[3/4] 上传训练数据..." -ForegroundColor Yellow

$dataDir = Join-Path $PROJECT_DIR "data"
if (Test-Path $dataDir) {
    scp -P $PORT -r $dataDir "$USER@$HOST`:$REMOTE_DIR/"
    Write-Host "✅ 训练数据上传完成" -ForegroundColor Green
} else {
    Write-Host "⚠️ data 目录不存在，跳过" -ForegroundColor Yellow
}

# ==================== 4. 提示下一步 ====================
Write-Host "`n[4/4] 上传完成！" -ForegroundColor Green
Write-Host ""
Write-Host "下一步：在 AutoDL 上执行以下命令" -ForegroundColor Cyan
Write-Host ""
Write-Host "ssh -p $PORT $USER@$HOST" -ForegroundColor White
Write-Host ""
Write-Host "# 在 AutoDL 上执行：" -ForegroundColor Gray
Write-Host "cd /root" -ForegroundColor White
Write-Host "tar -xzf $TEMP_DIR/project.tar.gz -C $REMOTE_DIR" -ForegroundColor White
Write-Host "cd $REMOTE_DIR" -ForegroundColor White
Write-Host "bash scripts/autodl_deploy.sh" -ForegroundColor White
Write-Host ""
Write-Host "注意：模型会在 AutoDL 上通过 ModelScope 内网下载，不需要上传" -ForegroundColor Yellow
