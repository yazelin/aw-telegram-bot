# v4 Video Download + User Whitelist Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `/download <url>` video download via yt-dlp and a user/chat whitelist in the CF Worker.

**Architecture:** Two independent features. (1) CF Worker gets a two-layer whitelist (ALLOWED_USERS + ALLOWED_CHATS) checked before dispatching to GitHub Actions. (2) Workflow gets two new safe-inputs handlers (`download-video` for yt-dlp download, `send-telegram-video` for Telegram upload) plus a skill script at `.github/skills/yt-dlp/download.py`, with prompt updated for `/download` routing.

**Tech Stack:** gh-aw, Copilot (gpt-5.3-codex), yt-dlp (pip), Cloudflare Workers, Telegram Bot API

---

### Task 1: Add whitelist to CF Worker

**Files:**
- Modify: `worker/src/index.js:35-38` (add whitelist check after text message filter)
- Modify: `worker/wrangler.toml` (add `[vars]` section)

**Step 1: Add `[vars]` to `worker/wrangler.toml`**

Current file:

```toml
name = "telegram-github-relay"
main = "src/index.js"
compatibility_date = "2024-01-01"
```

Add at the end:

```toml

[vars]
ALLOWED_USERS = "850654509"
ALLOWED_CHATS = ""
```

**Step 2: Add whitelist check to `worker/src/index.js`**

In the `handleWebhook` function, after the text message check (line 38) and before the dispatch (line 40-41), add the whitelist logic.

Replace lines 35-43:

```javascript
  // Only process text messages
  if (!update.message?.text) {
    return new Response("OK", { status: 200 });
  }

  // Fire-and-forget: dispatch to GitHub
  ctx.waitUntil(dispatchToGitHub(update, env));

  return new Response("OK", { status: 200 });
```

With:

```javascript
  // Only process text messages
  if (!update.message?.text) {
    return new Response("OK", { status: 200 });
  }

  // Whitelist check: user ID or chat ID must be allowed
  const msg = update.message;
  const userId = String(msg.from?.id || "");
  const chatId = String(msg.chat.id);
  const allowedUsers = (env.ALLOWED_USERS || "").split(",").filter(Boolean);
  const allowedChats = (env.ALLOWED_CHATS || "").split(",").filter(Boolean);

  if (!allowedUsers.includes(userId) && !allowedChats.includes(chatId)) {
    return new Response("OK", { status: 200 });
  }

  // Fire-and-forget: dispatch to GitHub
  ctx.waitUntil(dispatchToGitHub(update, env));

  return new Response("OK", { status: 200 });
```

Note: `.filter(Boolean)` removes empty strings so `ALLOWED_CHATS=""` doesn't match everything.

**Step 3: Commit**

```bash
cd /home/ct/gh-aw/aw-telegram-bot
git add worker/src/index.js worker/wrangler.toml
git commit -m "feat: add user/chat whitelist to CF Worker"
```

---

### Task 2: Deploy CF Worker and test whitelist

**Step 1: Deploy the worker**

```bash
cd /home/ct/gh-aw/aw-telegram-bot/worker
npx wrangler deploy
```

Expected: Deployment succeeds, shows the worker URL.

**Step 2: Test allowed user**

Send a message to the Telegram bot from your account (user ID 850654509).

Expected: Bot responds normally (workflow triggered in GitHub Actions).

**Step 3: Verify in GitHub Actions**

```bash
gh run list --repo yazelin/aw-telegram-bot --limit 3
```

Expected: A new run triggered by your message.

**Step 4: Commit any fixes if needed**

---

### Task 3: Create yt-dlp download skill script

**Files:**
- Create: `.github/skills/yt-dlp/download.py`

**Step 1: Create the skills directory**

```bash
mkdir -p /home/ct/gh-aw/aw-telegram-bot/.github/skills/yt-dlp
```

**Step 2: Create `download.py`**

Create `.github/skills/yt-dlp/download.py` with:

```python
#!/usr/bin/env python3
"""
yt-dlp download skill.

Usage: python download.py <url>
Output: JSON to stdout
  Success: {"ok": true, "file_path": "...", "title": "...", "filesize": 12345}
  Failure: {"ok": false, "error": "..."}

Downloads video in pre-merged 360p format (no ffmpeg required).
"""

import json
import os
import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "No URL provided"}))
        sys.exit(1)

    url = sys.argv[1]
    output_dir = "/tmp/yt-dlp-output"
    os.makedirs(output_dir, exist_ok=True)

    # Use video ID for safe filenames
    output_template = os.path.join(output_dir, "%(id)s.%(ext)s")

    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "yt_dlp",
                "-f", "b[height<=360]/b",  # pre-merged 360p, fallback to best pre-merged
                "-o", output_template,
                "--no-playlist",
                "--no-overwrites",
                "--restrict-filenames",
                "--print-json",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=240,
        )
    except subprocess.TimeoutExpired:
        print(json.dumps({"ok": False, "error": "Download timed out (240s)"}))
        sys.exit(1)

    if result.returncode != 0:
        error_msg = result.stderr.strip()[-500:] if result.stderr else "Unknown error"
        print(json.dumps({"ok": False, "error": error_msg}))
        sys.exit(1)

    # Parse yt-dlp JSON output (last line, in case of progress output)
    try:
        lines = result.stdout.strip().split("\n")
        info = json.loads(lines[-1])
    except (json.JSONDecodeError, IndexError):
        print(json.dumps({"ok": False, "error": "Failed to parse yt-dlp output"}))
        sys.exit(1)

    filepath = info.get("_filename", "")
    if not filepath or not os.path.exists(filepath):
        # Try to find the file in output_dir
        files = os.listdir(output_dir)
        if files:
            filepath = os.path.join(output_dir, files[0])
        else:
            print(json.dumps({"ok": False, "error": "Downloaded file not found"}))
            sys.exit(1)

    filesize = os.path.getsize(filepath)
    title = info.get("title", "Unknown")

    print(json.dumps({
        "ok": True,
        "file_path": filepath,
        "title": title,
        "filesize": filesize,
    }))


if __name__ == "__main__":
    main()
```

**Step 3: Commit**

```bash
cd /home/ct/gh-aw/aw-telegram-bot
git add .github/skills/yt-dlp/download.py
git commit -m "feat: add yt-dlp download skill script"
```

---

### Task 4: Add download-video and send-telegram-video safe-inputs

**Files:**
- Modify: `.github/workflows/telegram-bot.md:58-122` (safe-inputs section)

**Step 1: Add `download-video` safe-inputs handler**

After the existing `send-telegram-photo:` block (after line 122), add:

```yaml

  download-video:
    description: "Download a video from a URL using yt-dlp (360p, no ffmpeg)"
    inputs:
      url:
        type: string
        required: true
        description: "The video URL to download (YouTube, Twitter, etc.)"
    py: |
      import subprocess, sys, os, json
      url_val = inputs.get("url", "")
      if not url_val:
          print(json.dumps({"ok": False, "error": "No URL provided"}))
          raise SystemExit(1)
      # Install yt-dlp
      subprocess.check_call(
          [sys.executable, "-m", "pip", "install", "-q", "yt-dlp"],
          stdout=subprocess.DEVNULL
      )
      # Run skill script
      workspace = os.environ.get("GITHUB_WORKSPACE", "")
      script = os.path.join(workspace, ".github", "skills", "yt-dlp", "download.py")
      result = subprocess.run(
          [sys.executable, script, url_val],
          capture_output=True, text=True, timeout=240
      )
      if result.returncode != 0:
          error = result.stderr.strip()[-300:] if result.stderr else "Download failed"
          print(json.dumps({"ok": False, "error": error}))
      else:
          print(result.stdout)
    timeout: 300
```

**Step 2: Add `send-telegram-video` safe-inputs handler**

After the `download-video:` block, add:

```yaml

  send-telegram-video:
    description: "Send a video file to a Telegram chat"
    inputs:
      chat_id:
        type: string
        required: true
        description: "The Telegram chat ID to send the video to"
      video_path:
        type: string
        required: true
        description: "Absolute file path of the video to send"
      caption:
        type: string
        required: false
        description: "Optional caption for the video"
    py: |
      import os, json, urllib.request
      token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
      chat_id_val = inputs.get("chat_id", "")
      video_path = inputs.get("video_path", "")
      caption = inputs.get("caption", "")
      if not os.path.exists(video_path):
          print(json.dumps({"ok": False, "error": f"File not found: {video_path}"}))
          raise SystemExit(1)
      filesize = os.path.getsize(video_path)
      if filesize > 50 * 1024 * 1024:
          print(json.dumps({"ok": False, "error": f"File too large: {filesize} bytes (max 50MB)"}))
          raise SystemExit(1)
      boundary = "----YtDlpUpload"
      body = b""
      body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id_val}\r\n".encode()
      if caption:
          body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n".encode()
      with open(video_path, "rb") as f:
          video_data = f.read()
      filename = os.path.basename(video_path)
      body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"video\"; filename=\"{filename}\"\r\nContent-Type: video/mp4\r\n\r\n".encode()
      body += video_data
      body += f"\r\n--{boundary}--\r\n".encode()
      url = f"https://api.telegram.org/bot{token}/sendVideo"
      req = urllib.request.Request(url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
      resp = urllib.request.urlopen(req, timeout=120)
      data = json.loads(resp.read())
      print(json.dumps({"ok": True, "message_id": data.get("result", {}).get("message_id")}))
    env:
      TELEGRAM_BOT_TOKEN: "${{ secrets.TELEGRAM_BOT_TOKEN }}"
    timeout: 120
```

**Step 3: Compile and verify**

```bash
cd /home/ct/gh-aw/aw-telegram-bot
gh aw compile
```

Expected: 0 errors. Check that `.github/workflows/telegram-bot.lock.yml` now contains the new safe-inputs handlers.

**Step 4: Commit**

```bash
git add .github/workflows/telegram-bot.md .github/workflows/telegram-bot.lock.yml
git commit -m "feat: add download-video and send-telegram-video safe-inputs"
```

---

### Task 5: Update prompt for /download command routing

**Files:**
- Modify: `.github/workflows/telegram-bot.md:132-205` (prompt body after `---`)

**Step 1: Update the chatbot description line**

Change line 134-135 from:

```markdown
You are a helpful, friendly AI assistant responding to a Telegram message.
You can generate images, research topics, and translate text.
```

To:

```markdown
You are a helpful, friendly AI assistant responding to a Telegram message.
You can generate images, research topics, translate text, and download videos.
```

**Step 2: Add `/download` to the command prefix list**

Change lines 145-149 from:

```markdown
1. Check the message for a command prefix:
   - `/research <topic>` → Research mode
   - `/draw <description>` → Image generation mode
   - `/translate <text>` → Translation mode
   - No prefix → Auto-judge: pick the best mode based on content
```

To:

```markdown
1. Check the message for a command prefix:
   - `/research <topic>` → Research mode
   - `/draw <description>` → Image generation mode
   - `/translate <text>` → Translation mode
   - `/download <url>` → Video download mode
   - No prefix → Auto-judge: pick the best mode based on content
```

**Step 3: Update line 151 to include video**

Change:

```markdown
3. Always send exactly one response — either a photo or a text message.
```

To:

```markdown
3. Always send exactly one response — a photo, a video, or a text message.
```

**Step 4: Add video download workflow section**

After the Translation workflow section (after line 196) and before General guidelines (line 198), add:

```markdown

## Video download workflow

Use this when the user asks to download a video from a URL.

1. Call `download-video` with the URL from the message
2. Check the response:
   - If `ok` is `false` → send error message via `send-telegram-message`
   - If `ok` is `true` → check `filesize`
3. If filesize ≤ 50,000,000 (50MB):
   - Call `send-telegram-video` with:
     - `chat_id`: the Chat ID from above
     - `video_path`: the `file_path` from step 2
     - `caption`: the video title from step 2
4. If filesize > 50,000,000:
   - Send a text message explaining the video is too large for Telegram (max 50MB)
   - Include the video title and actual file size in the message

### Video download guidelines

- Supported sites: YouTube, Twitter/X, Instagram, and many more (any site yt-dlp supports)
- Videos are downloaded in 360p to keep file size manageable
- Only single videos are supported (no playlists)
- If the URL is invalid or unsupported, explain clearly and suggest alternatives
```

**Step 5: Compile and verify**

```bash
gh aw compile
```

Expected: 0 errors.

**Step 6: Commit**

```bash
git add .github/workflows/telegram-bot.md .github/workflows/telegram-bot.lock.yml
git commit -m "feat: add /download command routing and video download workflow"
```

---

### Task 6: Push and test all modes

**Step 1: Push all changes**

```bash
cd /home/ct/gh-aw/aw-telegram-bot
git push
```

**Step 2: Test video download**

Send to Telegram bot: `/download https://www.youtube.com/watch?v=dQw4w9WgXcQ`

Expected: Bot downloads the video and sends it back as a video message with title as caption (~1-2 min).

**Step 3: Test text message (regression)**

Send to Telegram bot: `你好`

Expected: Bot replies with a friendly text message.

**Step 4: Test image generation (regression)**

Send to Telegram bot: `/draw 一隻柴犬在海邊`

Expected: Bot sends back a photo with caption.

**Step 5: Test research mode (regression)**

Send to Telegram bot: `/research 2026年AI最新趨勢`

Expected: Bot sends back a research report with sources.

**Step 6: Check workflow logs if any test fails**

```bash
gh run list --repo yazelin/aw-telegram-bot --limit 5
gh run view <RUN_ID> --repo yazelin/aw-telegram-bot --log 2>&1 | grep -i "yt.dlp\|download\|video\|error\|fail" | head -30
```

Possible failure points:
- `pip install yt-dlp` fails → check runner has Python + pip
- yt-dlp can't find pre-merged 360p format → fallback `b` should handle this
- `GITHUB_WORKSPACE` not set → check if safe-inputs have access to this env var; if not, try hardcoding the path
- Video > 50MB at 360p → agent should catch this and send text message instead
- Telegram sendVideo fails → check multipart boundary, file path, Content-Type
- Skill script not found → verify `.github/skills/yt-dlp/download.py` is committed and pushed

**Step 7: Commit any fixes if needed**

```bash
git add -A
git commit -m "fix: adjust v4 config based on testing"
git push
```

---

### Task 7: Create v4 branch and tag

After all tests pass:

**Step 1: Tag the current state**

```bash
git tag v4-video-download
git push origin refs/tags/v4-video-download:refs/tags/v4-video-download
```

**Step 2: Create a preservation branch**

```bash
git checkout -b v4-video-download
git push origin refs/heads/v4-video-download:refs/heads/v4-video-download
git checkout main
```

---

### Troubleshooting Reference

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Bot ignores all messages | Whitelist blocking | Check ALLOWED_USERS in wrangler.toml matches your user ID |
| `pip install yt-dlp` fails | Network issue on runner | safe-inputs run outside firewall, should work; retry |
| yt-dlp "no video formats" | No pre-merged 360p available | Fallback `b` in format string handles this |
| "File not found" in send-telegram-video | GITHUB_WORKSPACE wrong or script path issue | Check env var; try hardcoding workspace path |
| Video upload timeout | File too large or slow upload | Check filesize < 50MB; increase send-telegram-video timeout |
| Agent doesn't recognize /download | Prompt routing unclear | Check prompt has `/download` in command prefix list |
| Compile error | YAML syntax in new safe-inputs | Check indentation; `py: \|` must be properly formatted |
| Whitelist empty string match | `"".split(",")` returns `[""]` | `.filter(Boolean)` in worker code prevents this |
