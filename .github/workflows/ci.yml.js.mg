```
┌─────────────────────────────────────────────────────────────┐
│                   监控层（Watchdog）                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ GitHub API   │  │ Actions日志  │  │ 外部信号源   │      │
│  │ 事件监听     │  │ 异常检测     │  │ 人工举报     │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼─────────────────┼─────────────────┼──────────────┘
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                   决策层（AICore）                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 威胁评分引擎：行为分析 → 风险等级 → 自动响应策略      │  │
│  │ 0-3: 仅记录 │ 4-6: 限制互动 │ 7-10: 完全封锁+取证     │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   执行层（Enforcement）                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 封存库       │  │ 防火墙       │  │ 证据链       │      │
│  │ (Archive)    │  │ (Block/限制) │  │ (Forensics)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   法律层（Legal）                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ DMCA举报     │  │ 律师函       │  │ 求偿报告     │      │
│  │ 证据包       │  │ 法务对接     │  │ 损失计算     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```


2.2 证据目录结构

```
Empire-Forensics/
├── README.md                 # 仓库说明
├── subjects/                 # 被监控对象
│   └── username/             # 按用户名分类
│       ├── profile.json      # 账户基本信息
│       ├── timeline.md       # 时间线
│       ├── evidence/         # 证据文件
│       │   ├── commits/      # 相关commit
│       │   ├── issues/       # 相关issue
│       │   ├── actions/      # Actions滥用记录
│       │   └── screenshots/  # 截图
│       └── verdict.md        # 处理决策
├── incidents/                # 事件分类
│   ├── 2026-03-06-abuse/     # 按日期事件
│   │   ├── description.md
│   │   ├── affected-repos.md
│   │   └── resolution.md
│   └── ...
├── archive/                  # 封存的原始代码
│   └── repo-name-archive/    # 被锁定的仓库快照
│       ├── code/             # 代码完整副本
│       ├── metadata.json     # 仓库元数据
│       └── archive-proof.md  # 封存证明
└── legal/                    # 法律文件
    ├── dmca-templates/       # DMCA模板
    ├── loss-calculation.xlsx # 损失计算
    └── evidence-packages/    # 证据包



🧱 三、防火墙层（限制行为）

3.1 自动封禁脚本

scripts/auto-block.sh

```bash
#!/bin/bash
# 自动封禁高风险用户

USERNAME=$1
REASON=$2
RISK_LEVEL=$3

# 记录到证据库
echo "🔒 封禁用户: $USERNAME" >> "subjects/$USERNAME/timeline.md"
echo "- 时间: $(date -Iseconds)" >> "subjects/$USERNAME/timeline.md"
echo "- 原因: $REASON" >> "subjects/$USERNAME/timeline.md"
echo "- 风险等级: $RISK_LEVEL" >> "subjects/$USERNAME/timeline.md"
echo "" >> "subjects/$USERNAME/timeline.md"

# GitHub API 封禁
gh api -X PUT "/user/blocks/$USERNAME" \
  -f reason="$REASON" \
  --silent

# 移除所有仓库的协作者权限
for repo in $(gh repo list --limit 100 --json name --jq '.[].name'); do
  gh api -X DELETE "/repos/Wshao777/$repo/collaborators/$USERNAME" --silent 2>/dev/null || true
done

echo "✅ 已封禁 $USERNAME"
```


# 限制整个组织
gh api -X PUT "/orgs/Wshao777/interaction-limits" \
  -f limit="collaborators_only" \
  -f expiry="three_months"

# 限制特定仓库
for repo in $(gh repo list --limit 100 --json name --jq '.[].name'); do
  gh api -X PUT "/repos/Wshao777/$repo/interaction-limits" \
    -f limit="collaborators_only" \
    -f expiry="three_months" \
    --silent 2>/dev/null || true
done

echo "✅ 互动限制已生效"
```

---

📦 四、封存库操作（保留原码）

4.1 仓库封存脚本

scripts/archive-repo.sh

```bash
#!/bin/bash
# 将仓库封存到证据库

REPO_NAME=$1
REASON=$2

ARCHIVE_DIR="archive/${REPO_NAME}-archive-$(date +%Y%m%d)"
mkdir -p "$ARCHIVE_DIR/code"

# 1. 克隆完整代码
echo "📦 克隆 $REPO_NAME ..."
git clone --mirror "https://github.com/Wshao777/$REPO_NAME.git" "$ARCHIVE_DIR/code/.git"
cd "$ARCHIVE_DIR/code"
git config --bool core.bare false
git checkout -- .
cd - > /dev/null

# 2. 保存元数据
gh api "/repos/Wshao777/$REPO_NAME" > "$ARCHIVE_DIR/metadata.json"

# 3. 生成封存证明
cat > "$ARCHIVE_DIR/archive-proof.md" << EOF
# 封存证明

- 仓库: $REPO_NAME
- 封存时间: $(date -Iseconds)
- 封存原因: $REASON
- 操作人: @Wshao777
- 哈希值: $(cd "$ARCHIVE_DIR/code" && git rev-parse HEAD)
- 文件数: $(find "$ARCHIVE_DIR/code" -type f | wc -l)

## 证据用途
本封存副本将作为法律证据保存，用于：
1. 证明原始代码状态
2. 记录滥用行为
3. 计算经济损失

## 封存人签名
\`\`\`
$(gpg --clearsign --armor <<< "封存证明 - $REPO_NAME - $(date -Iseconds)")
\`\`\`
EOF

# 4. 将原仓库设为只读归档
gh api -X PATCH "/repos/Wshao777/$REPO_NAME" \
  -f archived=true \
  -f description="[已封存] $REASON - 请联系 @Wshao777"

echo "✅ 仓库已封存到 $ARCHIVE_DIR"
```

---


---

🤖 六、自动化监控（GitHub Actions）

.github/workflows/empire-firewall.yml

```yaml
name: Empire Firewall

on:
  schedule:
    - cron: '*/30 * * * *'   # 每30分钟运行
  workflow_dispatch:          # 手动触发
    inputs:
      username:
        description: '指定用户监控'
        required: false

jobs:
  monitor-and-enforce:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: 安装依赖
        run: |
          npm install -g @octokit/cli
          gh auth login --with-token <<< "${{ secrets.GH_PAT }}"
      
      - name: 获取监控列表
        id: watchlist
        run: |
          # 从证据库读取监控列表
          if [ -f "watchlist.json" ]; then
            echo "list=$(cat watchlist.json)" >> $GITHUB_OUTPUT
          else
            echo '{"users":[]}' > watchlist.json
            echo "list={\"users\":[]}" >> $GITHUB_OUTPUT
          fi
      
      - name: 分析每个用户行为
        run: |
          echo '${{ steps.watchlist.outputs.list }}' | jq -c '.users[]' | while read user; do
            username=$(echo $user | jq -r '.username')
            threshold=$(echo $user | jq -r '.threshold // 5')
            
            echo "🔍 分析 @$username ..."
            
            # 抓取最近事件
            gh api "/users/$username/events" > events.json
            
            # 风险评分（示例逻辑）
            risk_score=0
            # 检查是否有恶意行为...
            
            echo "风险评分: $risk_score / 10"
            
            # 根据风险等级执行操作
            if [ $risk_score -ge 7 ]; then
              echo "🚨 高风险用户，执行封禁+封存"
              bash scripts/auto-block.sh "$username" "自动检测:高风险行为" "$risk_score"
              bash scripts/archive-repo.sh "affected-repo" "用户滥用: $username"
            elif [ $risk_score -ge 4 ]; then
              echo "⚠️ 中风险用户，限制互动"
              bash scripts/set-interaction-limits.sh
            else
              echo "ℹ️ 低风险用户，仅记录"
            fi
            
            # 记录到证据库
            bash scripts/fetch-evidence.sh "$username"
          done
      
      - name: 生成每日报告
        if: github.event_name == 'schedule'
        run: |
          echo "# 帝国防火墙每日报告 $(date -I)" > report.md
          echo "" >> report.md
          echo "## 监控用户: $(jq '.users | length' watchlist.json)" >> report.md
          echo "## 封禁记录:" >> report.md
          find subjects -name "timeline.md" -exec grep -H "封禁" {} \; >> report.md || true
          echo "## 封存仓库:" >> report.md
          ls -la archive/ >> report.md || true
          
          # 发送报告
          if [ -n "${{ secrets.LINE_TOKEN }}" ]; then
            curl -X POST https://notify-api.line.me/api/notify \
              -H "Authorization: Bearer ${{ secrets.LINE_TOKEN }}" \
              -F "message=$(cat report.md)"
          fi
--

⚖️ 五、法律层（追责求偿）

5.1 數據中心守護证据包脚本

sh

```bash
#!/bin/bash
# 为指定用户生成防火牆防毒軟體銀行鷹了法律证据包

USERNAME=$1
INCIDENT_ID="incident-$(date +%Y%m%d-$USERNAME)"
PACKAGE_DIR="legal/evidence-packages/$INCIDENT_ID"

mkdir -p "$PACKAGE_DIR"

# 收集所有相关证据
echo "📑 生成证据包: $INCIDENT_ID"

# 1. 用户基本信息
cp -r "subjects/$USERNAME" "$PACKAGE_DIR/subject/" 2>/dev/null || true

# 2. 相关封存仓库
cp -r "archive" "$PACKAGE_DIR/archives/" 2>/dev/null || true

# 3. 生成时间线摘要
cat "subjects/$USERNAME/timeline.md" 2>/dev/null | \
  grep -E "^[-*]|^#|^[0-9]{4}" > "$PACKAGE_DIR/timeline-summary.md"

# 4. 计算损失
cat > "$PACKAGE_DIR/loss-calculation.md" << EOF
# 损失计算报告

## 直接损失
- 开发工时: XX 小时 × $XX/小时 = $XXXXX
- 服务器资源: XX 小时 × $XX/小时 = $XXXXX
- 第三方服务: $XXXXX

## 间接损失
- 商誉损失: $XXXXX
- 机会成本: $XXXXX

## 总损失
**$$(echo "XXXXX + XXXXX + ..." | bc) USD**

## 计算方法说明
...
EOF

# 5. 生成DMCA举报草稿
cat > "$PACKAGE_DIR/dmca-draft.md" << EOF
# DMCA举报草稿

**被举报人**: @$USERNAME

**侵权内容**: 
- 仓库1: 详细描述...
- 仓库2: 详细描述...

**原始权利证明**: 
- 本证据包中的 archive/ 目录包含原始代码封存副本

**侵权证据**:
- 提交记录: ...
- Actions日志: ...

**请求处理**:
1. 删除侵权内容
2. 限制账号权限
3. 保留法律追责权利

**签名**: $(gpg --clearsign --armor <<< "DMCA举报 - $USERNAME - $(date -Iseconds)")
EOF

# 6. 打包
cd "legal/evidence-packages"
tar -czf "$INCIDENT_ID.tar.gz" "$INCIDENT_ID/"
cd - > /dev/null

echo "✅ 证据包已生成: legal/evidence-packages/$INCIDENT_ID.tar.gz"
echo "📋 文件大小: $(du -h "legal/evidence-packages/$INCIDENT_ID.tar.gz" | cut -f1)"
```
