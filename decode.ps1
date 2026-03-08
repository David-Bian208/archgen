# 自闭症AI助教项目解码脚本 (Windows PowerShell)
# 使用方法：将autism_assistant.base64放在同一目录，右键选择"使用PowerShell运行"

Write-Host "🔧 自闭症AI助教项目解码工具" -ForegroundColor Cyan
Write-Host "========================================"

# 检查base64文件
if (-not (Test-Path "autism_assistant.base64")) {
    Write-Host "❌ 缺少 autism_assistant.base64 文件" -ForegroundColor Red
    Write-Host "📝 请确保 autism_assistant.base64 与本脚本在同一目录" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ 找到 autism_assistant.base64 文件" -ForegroundColor Green
Write-Host "📦 解码Base64数据..." -ForegroundColor Cyan

# 解码base64为tar.gz
try {
    $base64Content = Get-Content "autism_assistant.base64" -Raw
    $bytes = [System.Convert]::FromBase64String($base64Content)
    [System.IO.File]::WriteAllBytes("$PWD\autism_assistant.tar.gz", $bytes)
    Write-Host "✅ Base64解码完成" -ForegroundColor Green
}
catch {
    Write-Host "❌ Base64解码失败" -ForegroundColor Red
    Write-Host "⚠️  请检查base64文件完整性" -ForegroundColor Yellow
    exit 1
}

Write-Host "📂 解压项目文件..." -ForegroundColor Cyan

# 检查是否安装了tar（Windows 10+ 内置）
$tarAvailable = $false
if (Get-Command tar -ErrorAction SilentlyContinue) {
    $tarAvailable = $true
}

if ($tarAvailable) {
    # 使用系统tar解压
    tar -xzf autism_assistant.tar.gz
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ 项目解压完成" -ForegroundColor Green
    } else {
        Write-Host "❌ 解压失败，文件可能损坏" -ForegroundColor Red
        exit 1
    }
} else {
    # 提示用户手动解压
    Write-Host "⚠️  系统未安装tar命令" -ForegroundColor Yellow
    Write-Host "📦 已生成 autism_assistant.tar.gz 压缩文件" -ForegroundColor Cyan
    Write-Host "📝 请使用以下工具解压：" -ForegroundColor Cyan
    Write-Host "   - Windows: 使用7-Zip或WinRAR解压"
    Write-Host "   - 或安装Windows的tar工具" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "📁 解压后项目目录: autism_assistant\"
}

Write-Host ""
Write-Host "📁 项目目录: autism_assistant\" -ForegroundColor Cyan
Write-Host ""
Write-Host "🚀 接下来操作：" -ForegroundColor Cyan
Write-Host "1. cd autism_assistant"
Write-Host "2. 查看 README.md 了解项目详情"
Write-Host "3. 运行启动脚本:"
Write-Host "   - Linux/Mac: ./start.sh"
Write-Host "   - Windows: 双击 start.bat"
Write-Host ""

# 清理临时文件（可选）
$response = Read-Host "是否删除临时压缩文件? (y/N)"
if ($response -eq 'y' -or $response -eq 'Y') {
    Remove-Item "autism_assistant.tar.gz" -ErrorAction SilentlyContinue
    Write-Host "✅ 已删除临时文件" -ForegroundColor Green
}

Write-Host ""
Write-Host "🎉 解码完成！" -ForegroundColor Green