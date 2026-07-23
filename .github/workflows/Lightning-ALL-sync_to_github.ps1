# ===========================================
# 🧠 双核心主控 - 电脑版 → 手机版同步脚本
# ===========================================

$computerCorePath = "D:\Lightning-ALL"
$githubRepos = @(
    "Wshao777/StormCar820-Ai-main",
    "Wshao777/Wuliang-Thinking-AI-Data",
    "Wshao777/Data-Purification-Wuliang-AI",
    "Wshao777/wind-pricing",
    "Wshao777/Grok4_Strategic_Logistics-Ai",
    "Wshao777/DeepSeek-Grok-ChatGPT"
)

# 1. 更新本地子模块（如果有）
Write-Host "🔁 更新电脑版核心代码..." -ForegroundColor Cyan
Set-Location $computerCorePath
git pull origin main 2>$null

# 2. 将电脑版核心内容同步到每个 GitHub 仓库
foreach ($repo in $githubRepos) {
    $repoName = $repo.Split('/')[1]
    $localClonePath = "$env:TEMP\$repoName"
    
    Write-Host "📤 同步到 $repo ..." -ForegroundColor Yellow
    if (Test-Path $localClonePath) {
        Remove-Item -Recurse -Force $localClonePath
    }
    git clone "https://github.com/$repo.git" $localClonePath
    Copy-Item -Path "$computerCorePath\*" -Destination $localClonePath -Recurse -Force
    Set-Location $localClonePath
    git add .
    git commit -m "Auto-sync from computer core at $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    git push origin main
    Set-Location $computerCorePath
    Remove-Item -Recurse -Force $localClonePath
}

Write-Host "✅ 同步完成！" -ForegroundColor Green