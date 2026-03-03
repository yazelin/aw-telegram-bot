# App Factory Design

## 概述

透過 Telegram 指令自動建立 GitHub repo、規劃工作項目、交由 AI agent 自主開發完成的端到端自動化系統。

## 使用者流程

```
/app 建立一個網頁版的踩地雷遊戲
  → gh-aw Copilot 評估可行性 + 技術選型 + 搜尋現有方案
  → 建 repo (yazelin/minesweeper-web)
  → push README.md + AGENTS.md + Skills + Workflows
  → 批次建 issue
  → 通知使用者 repo 名稱

/build yazelin/minesweeper-web
  → 觸發新 repo 的 implement.yml
  → Copilot CLI 自動撿 issue → 實作 → 開 PR
  → review.yml 自動 code review → merge → 撿下一個 issue
  → 全部完成後通知使用者

/msg yazelin/minesweeper-web#3 用 Canvas API 畫棋盤
  → 在 issue/PR 上留言
  → 如果是 agent-stuck issue，移除 label + 重新觸發 implement.yml
  → 通知使用者已傳達指示
```

## 架構決策

| 決策 | 選擇 | 原因 |
|------|------|------|
| 新 repo 位置 | 個人帳號（yazelin/xxx） | 簡單直接 |
| AI engine | Copilot CLI | 不需額外 API key，只要 Copilot 訂閱 |
| 模型 | gpt-5.3-codex | `--model gpt-5.3-codex` |
| 部署方式 | 依應用類型自動判斷 | 遊戲/網頁 → Pages, CLI → 只建 repo, API → CF Workers |
| Token 策略 | FACTORY_PAT (aw-telegram-bot) + GitHub App (新 repo) | 新 repo 的 token 限定單一 repo，1 小時過期自動刷新 |
| 觸發機制 | /build 手動觸發 | 使用者控制何時開始，避免意外燒分鐘數 |
| 自動連鎖 | review 通過後自動觸發下一輪 implement | /build 只按一次 |
| 通知機制 | 回呼 aw-telegram-bot/notify.yml | Telegram secrets 集中管理，不外洩 |
| 前置作業 | 方案 A：gh-aw safe-inputs + skill scripts | 不受防火牆限制，職責分離 |
| 新 repo template | 最小 template + 動態內容 | 固定 workflow + 動態 AGENTS.md/README |

## 系統元件

### 1. /app 指令（在 aw-telegram-bot gh-aw 裡）

#### 1.1 Copilot Agent 的規劃階段（「思考」）

```
1. 評估可行性
   ├─ 不可行 → send-telegram-message（詳述原因）→ 結束
   └─ 可行 → 繼續

2. 搜尋現有方案（策略層）
   ├─ 透過 web-search 搜尋開源專案
   ├─ 透過 safe-inputs 呼叫 gh search repos
   └─ 結論：從零開始 / 參考某專案 / fork 某專案

3. 技術選型（MVP 原則）
   ├─ 能用靜態就不用後端
   ├─ 能用原生就不用框架
   ├─ 能用 localStorage 就不用資料庫
   ├─ 能用 GitHub Pages 就不用 server
   └─ 依賴越少越好

4. 撰寫動態內容
   ├─ README.md（專案說明）
   ├─ AGENTS.md（專案規格 + 技術選型 + 參考資源 + 套件使用原則）
   └─ Issue 清單（標題 + body + acceptance criteria）

5. 選配 Skills
   └─ 根據技術選型選擇要帶哪些 skill templates
```

#### 1.2 Safe-inputs 的執行階段（「動手」）

每個 safe-input 對應一個 `.github/skills/app-factory/` 下的 Python skill script：

| Safe-input | Skill script | 功能 |
|------------|-------------|------|
| `create-repo` | `create_repo.py` | `gh repo create` |
| `setup-repo` | `setup_repo.py` | push 初始檔案（README + AGENTS.md + workflows + skills） |
| `create-issues` | `create_issues.py` | 批次 `gh issue create` |
| `setup-secrets` | `setup_secrets.py` | `gh secret set`（COPILOT_PAT） |
| `trigger-workflow` | `trigger_workflow.py` | `gh workflow run`（給 /build 用） |
| `post-comment` | `post_comment.py` | `gh issue comment` / `gh pr comment`（給 /msg 用） |
| `manage-labels` | `manage_labels.py` | 新增/移除 label（給 /msg 用） |

### 2. /build 指令（在 aw-telegram-bot gh-aw 裡）

簡單的 safe-input 呼叫：

```
Copilot agent 驗證 repo 存在
  → trigger-workflow(repo, "implement.yml")
  → send-telegram-message("🚀 已觸發開發")
```

### 2.5 /msg 指令（在 aw-telegram-bot gh-aw 裡）

使用者透過 Telegram 對新 repo 的 issue 或 PR 傳達指示。

```
/msg yazelin/minesweeper-web#3 用 Canvas API 畫棋盤，不要用 DOM
```

Copilot agent 解析後透過 safe-inputs 執行：

```
1. 解析指令
   ├─ repo = yazelin/minesweeper-web
   ├─ number = 3
   └─ message = "用 Canvas API 畫棋盤，不要用 DOM"

2. 判斷 #3 是 issue 還是 PR（gh CLI 可判斷）

3. 在 #3 上留言（safe-input: post-comment）
   └─ 格式："📝 來自使用者的指示：\n\n用 Canvas API 畫棋盤，不要用 DOM"

4. 如果是 issue 且有 agent-stuck label：
   ├─ 移除 agent-stuck label
   └─ 觸發 implement.yml（重新嘗試）

5. 如果是 PR 且有 needs-human-review label：
   ├─ 移除 needs-human-review label
   └─ 觸發 implement.yml（根據指示修改）

6. send-telegram-message("📝 已將指示傳達給 minesweeper-web #3，重新開始開發")
```

使用情境：

| 情境 | 指令 | 效果 |
|------|------|------|
| 解除 stuck | `/msg repo#3 改用 Canvas API` | 留言 + 移除 agent-stuck + 重新觸發 |
| 修改需求 | `/msg repo#2 按鈕改成藍色` | 留言在 issue，下次實作時參考 |
| 補充說明 | `/msg repo#5 API 要用 v2` | 補充資訊給 Copilot CLI |
| PR 意見 | `/msg repo#4 這邊加 error handling` | 留言在 PR，review/implement 時參考 |

### 3. 新 repo 結構

```
yazelin/minesweeper-web/
├── README.md                              ← agent 動態撰寫
├── AGENTS.md                              ← agent 動態撰寫
├── .github/
│   ├── skills/
│   │   ├── issue-workflow/SKILL.md        ← 固定 template（怎麼撿 issue、開 PR）
│   │   ├── code-standards/SKILL.md        ← 固定 template（commit/PR 規範）
│   │   ├── testing/SKILL.md               ← 固定 template（測試方法）
│   │   └── deploy-pages/SKILL.md          ← 依類型選配（GitHub Pages 部署）
│   └── workflows/
│       ├── implement.yml                  ← 固定 template（Copilot CLI 撿 issue）
│       └── review.yml                     ← 固定 template（Copilot CLI code review）
```

### 4. implement.yml（新 repo）

```yaml
name: Implement Issue
on:
  workflow_dispatch:

jobs:
  implement:
    runs-on: ubuntu-latest
    timeout-minutes: 120
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-node@v4
      - run: npm install -g @github/copilot

      - name: Implement
        env:
          COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_PAT }}
          GH_TOKEN: ${{ secrets.COPILOT_PAT }}
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

          copilot --autopilot --yolo \
            --model gpt-5.3-codex \
            --max-autopilot-continues 30 \
            -p "
              讀 AGENTS.md 了解專案規格。
              讀 .github/skills/ 了解開發規範。

              檢查目前狀態：
              1. 有 open PR 且有待處理的 review comments？
                 → 切到該 PR branch → 讀 comments → 修改 → push
                 → exit

              2. 沒有 open PR，有 open issue（排除 label:agent-stuck）？
                 → 撿最早的 open issue
                 → 建 branch (issue-N-slug)
                 → 實作（遵守 AGENTS.md 的技術選型）
                 → git add + commit + push
                 → gh pr create (body 包含 Closes #N)
                 → exit

              3. 沒有 open PR，沒有可做的 issue？
                 → 全部完成
                 → gh workflow run notify.yml --repo yazelin/aw-telegram-bot \
                      -f chat_id=850654509 \
                      -f text='✅ REPO_NAME 全部完成！'
                 → exit

              如果實作失敗或超時：
              → 在 issue 上留言說明原因
              → gh issue edit N --add-label agent-stuck
              → 觸發自己處理下一個 issue
            "
```

### 5. review.yml（新 repo）

```yaml
name: Code Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-node@v4
      - run: npm install -g @github/copilot

      - name: Count previous reviews
        id: count
        env:
          GH_TOKEN: ${{ secrets.COPILOT_PAT }}
        run: |
          COUNT=$(gh pr view ${{ github.event.pull_request.number }} \
            --json reviews --jq '.reviews | length')
          echo "review_count=$COUNT" >> "$GITHUB_OUTPUT"

      - name: Review
        env:
          COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_PAT }}
          GH_TOKEN: ${{ secrets.COPILOT_PAT }}
          REVIEW_COUNT: ${{ steps.count.outputs.review_count }}
        run: |
          if [ "$REVIEW_COUNT" -ge 3 ]; then
            gh issue edit ... --add-label needs-human-review
            gh workflow run notify.yml --repo yazelin/aw-telegram-bot \
              -f chat_id="850654509" \
              -f text="⚠️ REPO_NAME PR #N review 3 次未通過，需要人工協助"
            gh workflow run implement.yml
            exit 0
          fi

          copilot --autopilot \
            --model gpt-5.3-codex \
            --max-autopilot-continues 10 \
            -p "
              讀 AGENTS.md 了解專案規格。
              Review PR #${{ github.event.pull_request.number }}。

              如果程式碼品質 OK 且符合 issue 需求：
                1. gh pr review --approve
                2. gh pr merge --squash --delete-branch
                3. gh workflow run implement.yml（撿下一個 issue）
                4. gh workflow run notify.yml --repo yazelin/aw-telegram-bot \
                     -f chat_id=850654509 \
                     -f text='🔀 REPO_NAME PR #N 已 merge'

              如果有問題：
                1. gh pr review --request-changes -b '具體修改建議'
                2. gh workflow run implement.yml（回來修 PR）
            "
```

### 6. notify.yml（在 aw-telegram-bot）

```yaml
name: Send Telegram Notification
on:
  workflow_dispatch:
    inputs:
      chat_id:
        required: true
      text:
        required: true

jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - name: Verify caller
        run: |
          if [[ "${{ github.actor }}" != "yazelin" && \
                "${{ github.actor }}" != "github-actions[bot]" ]]; then
            echo "Unauthorized caller: ${{ github.actor }}"
            exit 1
          fi

      - name: Send Telegram message
        run: |
          curl -s -X POST \
            "https://api.telegram.org/bot${{ secrets.TELEGRAM_BOT_TOKEN }}/sendMessage" \
            -H "Content-Type: application/json" \
            -d '{"chat_id": "${{ inputs.chat_id }}", "text": "${{ inputs.text }}"}'
```

## 自動連鎖流程（完整）

```
/build（手動，一次）
  │
  ▼
implement.yml
  │
  ├─ Case A：有 open PR + review comments
  │   → 修改程式碼 → push
  │   → review.yml 自動觸發（PR synchronize）
  │
  ├─ Case B：沒有 open PR，有 open issue
  │   → 實作 → 開 PR
  │   → review.yml 自動觸發（PR opened）
  │
  └─ Case C：沒有 open PR，沒有 open issue
      → 全部完成 → notify → 停止

review.yml（自動觸發）
  │
  ├─ 已 review ≥ 3 次
  │   → 標記 needs-human-review → notify → 觸發 implement.yml（跳過）
  │
  ├─ Review 通過
  │   → merge PR → notify → 觸發 implement.yml（下一個 issue）
  │
  └─ Review 不通過
      → 留 comment → 觸發 implement.yml（回來修 PR）

implement.yml 失敗/超時
  → 標記 agent-stuck → 觸發自己（做下一個 issue）
  → 所有 issue 都 stuck → 沒有可做的 → notify → 停止
```

## 安全閥

| 防護 | 設定 | 目的 |
|------|------|------|
| implement timeout | 55 分鐘 | 低於 GitHub App token 1 小時限制 |
| review timeout | 30 分鐘 | review 不需要太久 |
| implement max continues | 30 | Copilot CLI 最多 30 輪 |
| review max continues | 10 | review 最多 10 輪 |
| review 失敗上限 | 3 次 | 超過標記 needs-human-review |
| implement 失敗 | 標記 agent-stuck | 跳過做下一個 |
| /build 手動觸發 | 使用者控制 | 避免意外燒分鐘數 |
| notify.yml caller 驗證 | github.actor 白名單 | 防止未授權觸發 |

## aw-telegram-bot 的 Skill Scripts 結構

```
.github/skills/
  yt-dlp/
    download.py                    ← 現有的
  app-factory/
    create_repo.py                 ← 建 repo
    setup_repo.py                  ← push 初始檔案
    create_issues.py               ← 批次建 issue
    setup_secrets.py               ← 設定 secrets
    trigger_workflow.py            ← 觸發 workflow
    post_comment.py                ← 留言到 issue/PR
    manage_labels.py               ← 新增/移除 label
    templates/
      skills/
        issue-workflow-SKILL.md    ← 固定 template
        code-standards-SKILL.md    ← 固定 template
        testing-SKILL.md           ← 固定 template
        deploy-pages-SKILL.md      ← 選配 template
      workflows/
        implement.yml              ← 固定 template
        review.yml                 ← 固定 template
```

## 需要準備的 Secrets

### aw-telegram-bot（建 repo 用）

| Secret | 用途 |
|--------|------|
| TELEGRAM_BOT_TOKEN | 傳送 Telegram 訊息 |
| FACTORY_PAT | Classic PAT (repo + workflow scope)，建 repo、設 secret、觸發 workflow |
| GEMINI_API_KEY | 現有的圖片生成 |
| TAVILY_API_KEY | 現有的搜尋 |
| APP_ID | GitHub App ID，用來產生新 repo 的 scoped token |
| APP_PRIVATE_KEY | GitHub App private key |

### 每個新 repo（Copilot CLI 用）

| Secret | 用途 |
|--------|------|
| APP_ID | GitHub App ID（跨 repo 共用值） |
| APP_PRIVATE_KEY | GitHub App private key（跨 repo 共用值） |

新 repo 不需要 PAT。每次 workflow run 時用 `actions/create-github-app-token` 動態產生只限該 repo 的 token（1 小時過期）。

### FACTORY_PAT 需要的 scope

- `repo`（建 repo、push workflow 檔案、管理 secrets）
- `workflow`（觸發 workflow）
- `admin:org`（如果未來改用 org，目前不需要）

## 技術選型原則（寫入 prompt）

Agent 在 /app 時遵守：
- 能用靜態就不用後端
- 能用原生就不用框架
- 能用 localStorage 就不用資料庫
- 能用 GitHub Pages 就不用 server
- 依賴越少越好，Copilot CLI 越容易成功
- MVP 優先，功能完整 > 程式碼完美
- 每個 issue 的範圍要小，Copilot CLI 必須能在 45 分鐘內完成（timeout 55 分鐘）

## Telegram 指令總覽

| 前綴 | 模式 | 功能 |
|------|------|------|
| `/app` | App Factory | 評估 + 建 repo + 建 issue |
| `/build` | Build | 觸發新 repo 的 implement.yml |
| `/msg` | Message | 對新 repo 的 issue/PR 留言 + 解除 stuck |
| `/download` | 影片下載 | yt-dlp 下載影片（現有） |
| `/research` | 研究 | Tavily + web-search（現有） |
| `/draw` | 繪圖 | nanobanana 生成圖片（現有） |
| `/translate` | 翻譯 | 純文字翻譯（現有） |
| 無前綴 | 自動判斷 | Agent 根據內容選擇（現有） |

## 通知時機

| 事件 | 誰觸發 | 訊息範例 |
|------|--------|---------|
| /app 完成建 repo | aw-telegram-bot | "✅ repo 已建好: yazelin/minesweeper-web，共 5 個 issue" |
| /app 評估不可行 | aw-telegram-bot | "❌ 無法建立：原因說明" |
| /build 已觸發 | aw-telegram-bot | "🚀 已觸發 yazelin/minesweeper-web 開發" |
| /msg 已傳達 | aw-telegram-bot | "📝 已將指示傳達給 minesweeper-web #3" |
| PR merge 成功 | 新 repo review.yml | "🔀 minesweeper-web PR #1 已 merge（1/5 done）" |
| 全部完成 | 新 repo implement.yml | "✅ minesweeper-web 全部完成！" |
| issue stuck | 新 repo implement.yml | "⚠️ minesweeper-web issue #3 卡住了" |
| review 多次不通過 | 新 repo review.yml | "⚠️ minesweeper-web PR #2 需要人工 review" |
