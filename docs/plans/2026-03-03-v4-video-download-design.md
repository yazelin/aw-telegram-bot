# aw-telegram-bot v4: Video Download + User Whitelist

## Goal

Add `/download <url>` command for video downloading via yt-dlp, plus a user/chat whitelist in the CF Worker to prevent unauthorized usage.

## Architecture

```
使用者：「/download https://youtube.com/watch?v=xxx」
  │
  ▼
Telegram → CF Worker（白名單檢查）→ GitHub Actions (workflow_dispatch)
  │
  ▼
Copilot Agent（判斷：/download 前綴 → 下載模式）
  │
  ├─ 1. download-video(url)          ← safe-inputs: pip install yt-dlp + 下載
  │     回傳 {file_path, title, filesize}
  │
  ├─ 2. 判斷 filesize < 50MB？
  │     ├─ 是 → send-telegram-video(chat_id, video_path, caption)
  │     └─ 否 → send-telegram-message(chat_id, "影片太大...")
  │
  ▼
使用者收到影片或提示訊息
```

## Scope

### In scope (v4)

- `/download <url>` command via yt-dlp
- safe-inputs: `download-video` (download only, return file path)
- safe-inputs: `send-telegram-video` (send only, accept file path)
- Skills architecture: `.github/skills/yt-dlp/download.py`
- CF Worker user/chat whitelist (ALLOWED_USERS + ALLOWED_CHATS)
- Fixed 360p, no ffmpeg, pre-merged formats

### Out of scope (future)

- GitHub Release for >50MB files
- ffmpeg post-processing (higher quality, format conversion)
- Audio-only download
- Playlist support
- Progress reporting during download

## Feature 1: Video Download

### Command Routing

| Prefix | Mode | Tools |
|--------|------|-------|
| `/download <url>` | Video download | download-video + send-telegram-video |
| `/research <topic>` | Research | Tavily + web-search + web-fetch |
| `/draw <description>` | Image generation | nanobanana generate_image |
| `/translate <text>` | Translation | None (agent translates directly) |
| No prefix | Auto-judge | Agent picks the best mode |

### Components

#### 1. Skills Architecture

```
.github/skills/
  yt-dlp/
    download.py     ← 實際下載邏輯，可獨立測試
```

`download.py` 負責：
- `pip install yt-dlp`（如果尚未安裝）
- 下載影片到 `/tmp/yt-dlp-output/`
- 固定 360p，使用預合併格式（不需要 ffmpeg）
- 回傳 JSON: `{"ok": true, "file_path": "...", "title": "...", "filesize": 12345}`

#### 2. safe-inputs: download-video

Thin wrapper，呼叫 skills script：

```yaml
safe-inputs:
  download-video:
    description: "Download a video from a URL using yt-dlp"
    inputs:
      url:
        type: string
        required: true
        description: "The video URL to download"
    py: |
      import subprocess, sys, json
      # Install yt-dlp
      subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "yt-dlp"])
      # Run skill script
      # ... (calls .github/skills/yt-dlp/download.py)
    timeout: 300
```

#### 3. safe-inputs: send-telegram-video

```yaml
safe-inputs:
  send-telegram-video:
    description: "Send a video to a Telegram chat"
    inputs:
      chat_id:
        type: string
        required: true
      video_path:
        type: string
        required: true
      caption:
        type: string
        required: false
    py: |
      # multipart upload to Telegram sendVideo API
    env:
      TELEGRAM_BOT_TOKEN: "${{ secrets.TELEGRAM_BOT_TOKEN }}"
    timeout: 120
```

#### 4. Separation of Concerns

```
download-video    → 只負責下載，回傳檔案路徑 + metadata
send-telegram-video → 只負責傳送，接收檔案路徑
Agent             → 串接兩者，判斷檔案大小
```

好處：
- 可重用：download-video 未來可搭配其他傳送方式
- 可測試：每個 handler 職責單一
- Agent 可以根據 metadata（filesize）決定下一步

### yt-dlp Configuration

```python
yt-dlp args:
  -f "b[height<=360]"    # 預合併格式，不需要 ffmpeg
  -o "/tmp/yt-dlp-output/%(title)s.%(ext)s"
  --no-playlist           # 不下載整個播放清單
  --print-json            # 輸出 JSON metadata
```

不安裝 ffmpeg 的原因：
- ubuntu-latest 沒有預裝 ffmpeg
- 安裝 ffmpeg 要 ~30 秒
- 預合併格式（`b[height<=360]`）已足夠 MVP 使用
- 360p 檔案通常 < 50MB

### Network

safe-inputs 在 AWF firewall 之外執行，不需要改 network allowlist。yt-dlp 可以存取任何網站。

### Timeout

維持 15 分鐘。yt-dlp 下載 360p 影片通常 < 1 分鐘。

## Feature 2: User/Chat Whitelist

### Implementation Location

**CF Worker**（不是 GitHub Actions）：
- 攔截時機早，不觸發 workflow
- 不消耗 Actions 分鐘數
- 毫秒級拒絕

### Two-Layer Whitelist

```
ALLOWED_USERS=850654509           ← 允許的使用者（from.id）
ALLOWED_CHATS=                    ← 允許的群組（chat.id），先留空
```

邏輯：
```javascript
const userId = String(msg.from?.id || "");
const chatId = String(msg.chat.id);
const allowedUsers = (env.ALLOWED_USERS || "").split(",");
const allowedChats = (env.ALLOWED_CHATS || "").split(",");

if (!allowedUsers.includes(userId) && !allowedChats.includes(chatId)) {
  return new Response("OK", { status: 200 });  // 靜默忽略
}
```

行為：
- 使用者在 ALLOWED_USERS → 放行（私聊、群組都行）
- chat 在 ALLOWED_CHATS → 放行（群組裡任何人都能用）
- 都不在 → 靜默忽略（不回應）

### Wrangler 設定

```toml
[vars]
ALLOWED_USERS = "850654509"
ALLOWED_CHATS = ""
```

改白名單只需要改 wrangler.toml 或 CF dashboard，不用改程式碼。

## Key Risks

| Risk | Mitigation |
|------|-----------|
| yt-dlp 下載超時 | safe-inputs timeout: 300 秒；360p 通常 < 1 分鐘 |
| 影片 > 50MB | MVP: 告知使用者太大，未來可用 GitHub Release |
| yt-dlp 不支援某網站 | 回傳錯誤訊息，建議使用者換網址 |
| pip install 失敗 | yt-dlp 是純 Python，pip install 極少失敗 |
| 白名單設定錯誤 | 靜默忽略，不會暴露錯誤訊息 |

## Decision Log

- **safe-inputs over MCP**: 不需要 Docker，不需要 allowlist，直接在 runner 執行
- **pip install over uvx**: runner 沒有 uv/uvx，pip 最簡單
- **不裝 ffmpeg**: 預合併格式足夠 MVP，省 30 秒安裝時間
- **360p 固定解析度**: 確保檔案 < 50MB，符合 Telegram 限制
- **download/send 分離**: 職責分離，可重用，可獨立測試
- **白名單在 CF Worker**: 攔截早，不浪費 Actions 分鐘數
- **兩層白名單**: ALLOWED_USERS（跨 chat）+ ALLOWED_CHATS（群組全員）
- **Skills 架構**: `.github/skills/` 放可重用 Python scripts，safe-inputs 當 thin wrapper
