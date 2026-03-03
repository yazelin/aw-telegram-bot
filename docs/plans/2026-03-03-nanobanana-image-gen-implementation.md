# nanobanana Image Generation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add AI image generation to the Telegram bot via nanobanana-py MCP server, so users can request images by text and receive them as Telegram photos.

**Architecture:** nanobanana-py runs as an MCP server on the GitHub Actions runner (launched via `uvx`). The Copilot agent calls its `generate_image` tool, gets a file path back, then calls a `send-telegram-photo` safe-inputs tool that reads the file and uploads it to Telegram via `sendPhoto` multipart API.

**Tech Stack:** gh-aw, Copilot (gpt-5.3-codex), nanobanana-py (Gemini API), Python safe-inputs, Cloudflare Worker (unchanged)

---

### Task 1: Add GEMINI_API_KEY secret to GitHub repo

**Step 1: Set the secret**

```bash
gh secret set GEMINI_API_KEY --repo yazelin/aw-telegram-bot
```

Paste the Gemini API key when prompted.

**Step 2: Verify**

```bash
gh secret list --repo yazelin/aw-telegram-bot
```

Expected: `GEMINI_API_KEY` appears in the list alongside `COPILOT_GITHUB_TOKEN` and `TELEGRAM_BOT_TOKEN`.

---

### Task 2: Add nanobanana-py MCP server to workflow frontmatter

**Files:**
- Modify: `.github/workflows/telegram-bot.md:1-63` (frontmatter section)

**Step 1: Add `mcp-servers:` section**

After the `tools:` block and before `safe-inputs:`, add:

```yaml
mcp-servers:
  - name: nanobanana
    command: uvx
    args: [nanobanana-py]
    env:
      NANOBANANA_GEMINI_API_KEY: "${{ secrets.GEMINI_API_KEY }}"
      NANOBANANA_OUTPUT_DIR: "/tmp/nanobanana-output"
    allowed: [generate_image]
```

**Step 2: Add `generativelanguage.googleapis.com` to network allowlist**

Change:
```yaml
network:
  allowed:
    - defaults
    - api.telegram.org
```

To:
```yaml
network:
  allowed:
    - defaults
    - api.telegram.org
    - generativelanguage.googleapis.com
```

**Step 3: Add GEMINI_API_KEY to secrets section**

Change:
```yaml
secrets:
  TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
```

To:
```yaml
secrets:
  TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

**Step 4: Compile and verify**

```bash
gh aw compile
```

Expected: Compiles with 0 errors. May have warnings about experimental features.

**Step 5: Commit**

```bash
git add .github/workflows/telegram-bot.md .github/workflows/telegram-bot.lock.yml
git commit -m "feat: add nanobanana-py MCP server for image generation"
```

---

### Task 3: Add send-telegram-photo safe-inputs tool

**Files:**
- Modify: `.github/workflows/telegram-bot.md` (safe-inputs section)

**Step 1: Add the send-telegram-photo tool**

After the existing `send-telegram-message` safe-input and before `secrets:`, add:

```yaml
  send-telegram-photo:
    description: "Send a photo to a Telegram chat"
    inputs:
      chat_id:
        type: string
        required: true
        description: "The Telegram chat ID to send the photo to"
      photo_path:
        type: string
        required: true
        description: "Absolute file path of the image to send"
      caption:
        type: string
        required: false
        description: "Optional caption for the photo"
    py: |
      import os, json, urllib.request
      token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
      chat_id_val = inputs.get("chat_id", "")
      photo_path = inputs.get("photo_path", "")
      caption = inputs.get("caption", "")
      boundary = "----NanoBanana"
      body = b""
      body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id_val}\r\n".encode()
      if caption:
          body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n".encode()
      with open(photo_path, "rb") as f:
          photo_data = f.read()
      body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"image.png\"\r\nContent-Type: image/png\r\n\r\n".encode()
      body += photo_data
      body += f"\r\n--{boundary}--\r\n".encode()
      url = f"https://api.telegram.org/bot{token}/sendPhoto"
      req = urllib.request.Request(url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
      resp = urllib.request.urlopen(req)
      data = json.loads(resp.read())
      print(json.dumps({"ok": True, "message_id": data.get("result", {}).get("message_id")}))
    env:
      TELEGRAM_BOT_TOKEN: "${{ secrets.TELEGRAM_BOT_TOKEN }}"
    timeout: 120
```

**Step 2: Compile and verify**

```bash
gh aw compile
```

Expected: 0 errors.

**Step 3: Commit**

```bash
git add .github/workflows/telegram-bot.md .github/workflows/telegram-bot.lock.yml
git commit -m "feat: add send-telegram-photo safe-inputs tool"
```

---

### Task 4: Update workflow prompt for image generation

**Files:**
- Modify: `.github/workflows/telegram-bot.md` (prompt body, after `---`)

**Step 1: Replace the entire prompt body**

Replace everything after the closing `---` of frontmatter with:

```markdown
# Telegram Chatbot

You are a helpful, friendly AI assistant responding to a Telegram message.
You can generate images using the nanobanana tools.

## Message

- **Chat ID**: ${{ github.event.inputs.chat_id }}
- **Username**: ${{ github.event.inputs.username }}
- **Message**: ${{ github.event.inputs.text }}

## Instructions

1. Read the user's message above.
2. Decide if the request involves generating an image:
   - If yes: call `generate_image` with a detailed English prompt, then use `send-telegram-photo` to send the resulting file
   - If no: use `send-telegram-message` to send a text reply
3. Always send exactly one response — either a photo or a text message.

## Image generation workflow

1. Call `generate_image` with a descriptive prompt (always in English for best results)
2. The tool returns a file path (e.g. `/tmp/nanobanana-output/image.png`)
3. Call `send-telegram-photo` with:
   - `chat_id`: the Chat ID from above
   - `photo_path`: the file path from step 2
   - `caption`: a short description of what was generated (in the user's language)
4. If generation fails, use `send-telegram-message` to explain the error

## Guidelines

- Keep text responses under 4096 characters (Telegram limit)
- For image requests, write detailed prompts in English for better quality
- Add a brief caption in the user's language describing what was generated
- Respond in the same language the user writes in
- If you don't know something, say so honestly
```

**Step 2: Compile and verify**

```bash
gh aw compile
```

Expected: 0 errors.

**Step 3: Commit**

```bash
git add .github/workflows/telegram-bot.md .github/workflows/telegram-bot.lock.yml
git commit -m "feat: update prompt for image generation support"
```

---

### Task 5: Push and test

**Step 1: Push all changes**

```bash
git push
```

**Step 2: Test text message (regression)**

Send a text message to the Telegram bot (e.g. "你好"). Verify the bot replies with text as before.

**Step 3: Test image generation**

Send an image request to the Telegram bot (e.g. "畫一隻穿太空衣的貓"). Wait ~2 minutes.

Expected: Bot sends back a photo with a caption.

**Step 4: Check workflow logs if it fails**

```bash
gh run list --repo yazelin/aw-telegram-bot --limit 1
gh run view <RUN_ID> --repo yazelin/aw-telegram-bot --log 2>&1 | grep -i "nanobanana\|generate_image\|send.telegram.photo\|error\|fail" | head -30
```

Possible failure points:
- MCP server fails to start → check if `uvx` is available on runner
- Gemini API blocked by firewall → check firewall logs for `generativelanguage.googleapis.com`
- File path mismatch → check if nanobanana output dir matches safe-inputs read path
- Photo upload fails → check Telegram API response in safe-inputs logs

**Step 5: Commit any fixes if needed, then tag**

```bash
git push
```

---

### Troubleshooting reference

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| MCP server not found | `uvx` not on runner | Try `pip install nanobanana-py && nanobanana-py` in command/args |
| Gemini API timeout | Slow generation | Increase `NANOBANANA_TIMEOUT` env var |
| Firewall blocks Gemini | Domain not in allowlist | Verify `generativelanguage.googleapis.com` in network.allowed |
| File not found in send-telegram-photo | Path mismatch | Check `NANOBANANA_OUTPUT_DIR` matches what agent passes |
| Telegram rejects photo | File too large or wrong format | Check image size; nanobanana default 1K should be fine |
| Agent doesn't call generate_image | Prompt unclear | Refine prompt instructions |
