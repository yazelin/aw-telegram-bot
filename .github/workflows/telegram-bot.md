---
description: |
  Telegram chatbot powered by Copilot. Receives messages via workflow_dispatch
  from Cloudflare Worker relay, generates a response, and replies via Telegram API.

on:
  workflow_dispatch:
    inputs:
      chat_id:
        description: "Telegram chat ID"
        required: true
      text:
        description: "Message text"
        required: true
      username:
        description: "Telegram username"
        required: false

concurrency:
  group: "gh-aw-${{ github.workflow }}-${{ github.run_id }}"
  cancel-in-progress: false

engine:
  id: copilot
  model: gpt-5.3-codex

permissions:
  contents: read

network:
  allowed:
    - defaults
    - api.telegram.org
    - generativelanguage.googleapis.com
    - mcp.tavily.com
    - github.com

tools:
  web-fetch:
  web-search:

mcp-servers:
  nanobanana:
    container: ghcr.io/astral-sh/uv:python3.12-alpine
    args: [-v, /tmp:/tmp:rw]
    entrypointArgs: [uvx, nanobanana-py]
    env:
      NANOBANANA_GEMINI_API_KEY: "${{ secrets.GEMINI_API_KEY }}"
      NANOBANANA_OUTPUT_DIR: "/tmp/nanobanana-output"
      NANOBANANA_MODEL: "gemini-3-pro-image-preview"
      NANOBANANA_FALLBACK_MODELS: "gemini-3.1-flash-image-preview,gemini-2.5-flash-image"
      NANOBANANA_TIMEOUT: "120"
      NANOBANANA_DEBUG: "1"
    allowed: [generate_image]
  tavily:
    url: "https://mcp.tavily.com/mcp/?tavilyApiKey=${{ secrets.TAVILY_API_KEY }}"
    allowed: ["*"]

safe-inputs:
  send-telegram-message:
    description: "Send a text message to a Telegram chat"
    inputs:
      chat_id:
        type: string
        required: true
        description: "The Telegram chat ID to send the message to"
      text:
        type: string
        required: true
        description: "The message text to send"
    py: |
      import os, json, urllib.request
      token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
      chat_id_val = inputs.get("chat_id", "")
      text_val = inputs.get("text", "")
      url = f"https://api.telegram.org/bot{token}/sendMessage"
      payload = json.dumps({"chat_id": chat_id_val, "text": text_val}).encode()
      req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
      resp = urllib.request.urlopen(req)
      data = json.loads(resp.read())
      print(json.dumps({"ok": True, "message_id": data.get("result", {}).get("message_id")}))
    env:
      TELEGRAM_BOT_TOKEN: "${{ secrets.TELEGRAM_BOT_TOKEN }}"

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
      ext = os.path.splitext(filename)[1].lower()
      content_type = {"webm": "video/webm", "mkv": "video/x-matroska", "mp4": "video/mp4"}.get(ext.lstrip("."), "video/mp4")
      body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"supports_streaming\"\r\n\r\ntrue\r\n".encode()
      body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"video\"; filename=\"{filename}\"\r\nContent-Type: {content_type}\r\n\r\n".encode()
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

  create-repo:
    description: "Create a new GitHub repository"
    inputs:
      owner:
        type: string
        required: true
        description: "Repository owner (e.g. aw-apps)"
      name:
        type: string
        required: true
        description: "Repository name (e.g. minesweeper-web)"
      repo_description:
        type: string
        required: true
        description: "Short description for the repository"
    py: |
      import subprocess, sys, os, json
      owner = inputs.get("owner", "")
      name = inputs.get("name", "")
      desc = inputs.get("repo_description", "")
      repo = f"{owner}/{name}"
      workspace = os.environ.get("GITHUB_WORKSPACE", "")
      script = os.path.join(workspace, ".github", "skills", "app-factory", "create_repo.py")
      result = subprocess.run(
          [sys.executable, script, repo, desc],
          capture_output=True, text=True, timeout=60,
          env={**os.environ}
      )
      if result.returncode != 0:
          print(result.stdout or json.dumps({"ok": False, "error": result.stderr.strip()[-300:] or "Failed"}))
      else:
          print(result.stdout)
    env:
      GH_TOKEN: "${{ secrets.FACTORY_PAT }}"
    timeout: 60

  setup-repo:
    description: "Push initial files to a repository"
    inputs:
      repo:
        type: string
        required: true
        description: "Repository full name (e.g. aw-apps/minesweeper-web)"
      files_json:
        type: string
        required: true
        description: "JSON array of {path, content} objects to push"
    py: |
      import subprocess, sys, os, json
      repo = inputs.get("repo", "")
      files_json = inputs.get("files_json", "[]")
      workspace = os.environ.get("GITHUB_WORKSPACE", "")
      script = os.path.join(workspace, ".github", "skills", "app-factory", "setup_repo.py")
      result = subprocess.run(
          [sys.executable, script, repo, files_json],
          capture_output=True, text=True, timeout=120,
          env={**os.environ}
      )
      if result.returncode != 0:
          print(result.stdout or json.dumps({"ok": False, "error": result.stderr.strip()[-300:] or "Failed"}))
      else:
          print(result.stdout)
    env:
      GH_TOKEN: "${{ secrets.FACTORY_PAT }}"
    timeout: 120

  create-issues:
    description: "Create multiple issues in a repository"
    inputs:
      repo:
        type: string
        required: true
        description: "Repository full name (e.g. aw-apps/minesweeper-web)"
      issues_json:
        type: string
        required: true
        description: "JSON array of {title, body} objects"
    py: |
      import subprocess, sys, os, json
      repo = inputs.get("repo", "")
      issues_json = inputs.get("issues_json", "[]")
      workspace = os.environ.get("GITHUB_WORKSPACE", "")
      script = os.path.join(workspace, ".github", "skills", "app-factory", "create_issues.py")
      result = subprocess.run(
          [sys.executable, script, repo, issues_json],
          capture_output=True, text=True, timeout=120,
          env={**os.environ}
      )
      if result.returncode != 0:
          print(result.stdout or json.dumps({"ok": False, "error": result.stderr.strip()[-300:] or "Failed"}))
      else:
          print(result.stdout)
    env:
      GH_TOKEN: "${{ secrets.FACTORY_PAT }}"
    timeout: 120

  setup-secrets:
    description: "Set secrets on a repository"
    inputs:
      repo:
        type: string
        required: true
        description: "Repository full name"
      secrets_json:
        type: string
        required: true
        description: "JSON array of {name, value} objects"
    py: |
      import subprocess, sys, os, json
      repo = inputs.get("repo", "")
      secrets_json = inputs.get("secrets_json", "[]")
      workspace = os.environ.get("GITHUB_WORKSPACE", "")
      script = os.path.join(workspace, ".github", "skills", "app-factory", "setup_secrets.py")
      result = subprocess.run(
          [sys.executable, script, repo, secrets_json],
          capture_output=True, text=True, timeout=60,
          env={**os.environ}
      )
      if result.returncode != 0:
          print(result.stdout or json.dumps({"ok": False, "error": result.stderr.strip()[-300:] or "Failed"}))
      else:
          print(result.stdout)
    env:
      GH_TOKEN: "${{ secrets.FACTORY_PAT }}"
      COPILOT_TOKEN_VALUE: "${{ secrets.CHILD_COPILOT_TOKEN }}"
      COPILOT_PAT_VALUE: "${{ secrets.COPILOT_PAT }}"
      NOTIFY_TOKEN_VALUE: "${{ secrets.NOTIFY_TOKEN }}"
    timeout: 60

  trigger-workflow:
    description: "Trigger a workflow in a repository"
    inputs:
      repo:
        type: string
        required: true
        description: "Repository full name"
      workflow:
        type: string
        required: true
        description: "Workflow filename (e.g. implement.yml)"
    py: |
      import subprocess, sys, os, json
      repo = inputs.get("repo", "")
      workflow = inputs.get("workflow", "")
      workspace = os.environ.get("GITHUB_WORKSPACE", "")
      script = os.path.join(workspace, ".github", "skills", "app-factory", "trigger_workflow.py")
      result = subprocess.run(
          [sys.executable, script, repo, workflow],
          capture_output=True, text=True, timeout=30,
          env={**os.environ}
      )
      if result.returncode != 0:
          print(result.stdout or json.dumps({"ok": False, "error": result.stderr.strip()[-300:] or "Failed"}))
      else:
          print(result.stdout)
    env:
      GH_TOKEN: "${{ secrets.FACTORY_PAT }}"
    timeout: 30

  post-comment:
    description: "Post a comment on an issue or PR in any repo"
    inputs:
      repo:
        type: string
        required: true
        description: "Repository full name"
      number:
        type: string
        required: true
        description: "Issue or PR number"
      body:
        type: string
        required: true
        description: "Comment body text"
    py: |
      import subprocess, sys, os, json
      repo = inputs.get("repo", "")
      number = inputs.get("number", "")
      body = inputs.get("body", "")
      workspace = os.environ.get("GITHUB_WORKSPACE", "")
      script = os.path.join(workspace, ".github", "skills", "app-factory", "post_comment.py")
      result = subprocess.run(
          [sys.executable, script, repo, number, body],
          capture_output=True, text=True, timeout=30,
          env={**os.environ}
      )
      if result.returncode != 0:
          print(result.stdout or json.dumps({"ok": False, "error": result.stderr.strip()[-300:] or "Failed"}))
      else:
          print(result.stdout)
    env:
      GH_TOKEN: "${{ secrets.FACTORY_PAT }}"
    timeout: 30

  manage-labels:
    description: "Add or remove a label on an issue or PR"
    inputs:
      repo:
        type: string
        required: true
        description: "Repository full name"
      number:
        type: string
        required: true
        description: "Issue or PR number"
      action:
        type: string
        required: true
        description: "'add' or 'remove'"
      label:
        type: string
        required: true
        description: "Label name"
    py: |
      import subprocess, sys, os, json
      repo = inputs.get("repo", "")
      number = inputs.get("number", "")
      action = inputs.get("action", "")
      label = inputs.get("label", "")
      workspace = os.environ.get("GITHUB_WORKSPACE", "")
      script = os.path.join(workspace, ".github", "skills", "app-factory", "manage_labels.py")
      result = subprocess.run(
          [sys.executable, script, repo, number, action, label],
          capture_output=True, text=True, timeout=30,
          env={**os.environ}
      )
      if result.returncode != 0:
          print(result.stdout or json.dumps({"ok": False, "error": result.stderr.strip()[-300:] or "Failed"}))
      else:
          print(result.stdout)
    env:
      GH_TOKEN: "${{ secrets.FACTORY_PAT }}"
    timeout: 30

secrets:
  TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
  TAVILY_API_KEY: ${{ secrets.TAVILY_API_KEY }}
  FACTORY_PAT: ${{ secrets.FACTORY_PAT }}
  COPILOT_PAT: ${{ secrets.COPILOT_PAT }}
  CHILD_COPILOT_TOKEN: ${{ secrets.CHILD_COPILOT_TOKEN }}

timeout-minutes: 15
---

# Telegram Chatbot

You are a helpful, friendly AI assistant responding to a Telegram message.
You can generate images, research topics, translate text, download videos,
create app projects, trigger builds, and send messages to repos.

## Message

- **Chat ID**: ${{ github.event.inputs.chat_id }}
- **Username**: ${{ github.event.inputs.username }}
- **Message**: ${{ github.event.inputs.text }}

## Instructions

1. Check the message for a command prefix:
   - `/app <description>` → App Factory mode
   - `/build <owner/repo>` → Build trigger mode
   - `/msg <owner/repo>#<number> <message>` → Message relay mode
   - `/research <topic>` → Research mode
   - `/draw <description>` → Image generation mode
   - `/translate <text>` → Translation mode
   - `/download <url>` → Video download mode
   - No prefix → Auto-judge: pick the best mode based on content
2. Execute the appropriate workflow below.
3. Always send exactly one response — a photo, a video, or a text message.

## Research workflow

Use this when the user asks to research, investigate, fact-check, or asks questions that need up-to-date information.

1. Use Tavily search to find information on the topic (use search_depth "advanced" for better results)
2. Use web-search to search from additional angles or keywords
3. Use web-fetch to read 2-3 of the most important source URLs in full
4. Synthesize all findings into a structured report:
   - **Summary**: 3-5 sentences overview
   - **Key findings**: bullet points with the most important facts
   - **Sources**: numbered list of URLs with brief descriptions
5. Send the report via `send-telegram-message`
6. If research fails or finds nothing useful, explain what was tried and suggest alternative queries

### Research guidelines

- Always cross-reference: don't rely on a single source
- Limit to 3-5 sources to keep response time reasonable
- Include source URLs so the user can verify
- Prefer recent sources when the topic is time-sensitive
- Write the report in the same language the user writes in

## Image generation workflow

Use this when the user asks to draw, generate, or create an image.

1. Call `generate_image` with a descriptive prompt (always in English for best results)
2. The tool returns a file path (e.g. `/tmp/nanobanana-output/image.png`)
3. Call `send-telegram-photo` with:
   - `chat_id`: the Chat ID from above
   - `photo_path`: the file path from step 2
   - `caption`: a short description of what was generated (in the user's language)
4. If generation fails, use `send-telegram-message` to explain the error

## Translation workflow

Use this when the user asks to translate text.

1. Detect the source language
2. Translate to the target language:
   - If the user specifies a target language, use that
   - If not specified: Chinese → English, English → Chinese, other → Chinese
3. Send the translation via `send-telegram-message`
4. Include the original text and the translation clearly formatted

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

## App Factory workflow

Use this when the user sends `/app <description>` to create a new app project.

### Phase 1: Evaluate feasibility

1. Analyze the user's description to understand what they want
2. Evaluate if it's feasible as an MVP:
   - Is the scope reasonable for automated development?
   - Are there legal/security/privacy concerns?
   - Is it technically achievable with standard web technologies?
3. If NOT feasible, send a detailed explanation via `send-telegram-message` and stop

### Phase 2: Deep Research (Diverge)

1. Use `web-search` to find 2-3 similar open-source projects
2. Use `web-fetch` to read their README and file structure
3. Extract: typical modules, file organization, feature breakdown
4. Note which features are tightly coupled vs independent
5. Decide: build from scratch, reference an existing project, or suggest a fork

### Phase 3: Technical decisions (MVP principles)

Apply these rules strictly:
- Static over backend (use GitHub Pages if possible)
- Native over framework (pure HTML/CSS/JS over React/Vue)
- localStorage over database
- Zero dependencies preferred
- Fewer dependencies = higher chance of Copilot CLI success

Determine:
- **Repo name**: lowercase, hyphenated (e.g. `minesweeper-web`)
- **Tech stack**: specific languages, frameworks (or lack thereof)
- **Deploy target**: GitHub Pages / repo only / Cloudflare Workers

### Phase 4: Plan content

Write these in your mind (do NOT output them to chat):

1. **README.md**: Project title, description, tech stack, how to run locally, deploy info
2. **AGENTS.md**: Full project spec including:
   - Project goal
   - Tech stack with specific versions/choices
   - Architecture overview
   - References to open-source projects (if any)
   - Package usage principles
   - Acceptance criteria for the whole project
3. **Issue list**: 3-8 issues, each with:
   - Clear title
   - Detailed body with acceptance criteria
   - Ordered by implementation dependency (foundational first)
4. **Skills selection**: Pick from available templates:
   - Always include: `issue-workflow`, `code-standards`, `testing`
   - If deploying to Pages: include `deploy-pages`

### Phase 5: Execute

Call safe-inputs in this order:

1. `create-repo` with owner=`aw-apps`, name=`<repo-name>`, description
2. `setup-repo` with all files:
   - `README.md` (dynamic)
   - `AGENTS.md` (dynamic)
   - `.github/workflows/implement.yml` (from template, with PLACEHOLDER_NOTIFY_REPO replaced with `yazelin/aw-telegram-bot` and PLACEHOLDER_CHAT_ID replaced with the chat_id from this message)
   - `.github/workflows/review.yml` (from template, same placeholder replacements)
   - `.github/skills/issue-workflow/SKILL.md` (from template)
   - `.github/skills/code-standards/SKILL.md` (from template)
   - `.github/skills/testing/SKILL.md` (from template)
   - `.github/skills/deploy-pages/SKILL.md` (if applicable)
3. `create-issues` with the planned issues
4. `setup-secrets` with `[]` (COPILOT_PAT is auto-added by the script)
5. `send-telegram-message` with:
   - Summary: repo URL, number of issues created, tech stack chosen
   - Instructions: "Send `/build aw-apps/<repo-name>` to start development"

### App Factory guidelines

- Repo names should be descriptive and short (2-4 words, hyphenated)
- README should be in the user's language (Traditional Chinese)
- AGENTS.md should be in English (Copilot CLI works better in English)
- Issues should be in English with clear acceptance criteria
- Each issue should be independently implementable when possible
- **Each issue must be small enough for Copilot CLI to complete in under 45 minutes**
- Prefer more smaller issues (5-8) over fewer large ones (2-3)
- First issue should set up the project skeleton
- Last issue should handle deployment (if applicable)

## Build trigger workflow

Use this when the user sends `/build <owner/repo>`.

1. Parse the repo name from the message
2. Verify the repo exists by checking if `trigger-workflow` can reach it
3. Call `trigger-workflow` with repo and workflow=`implement.yml`
4. Send confirmation via `send-telegram-message`:
   "🚀 已觸發 <repo> 開發流程，可到 https://github.com/<repo>/actions 查看進度"

### Build trigger guidelines

- The repo must already exist (created by `/app`)
- If the repo doesn't exist, explain that they need to run `/app` first

## Message relay workflow

Use this when the user sends `/msg <owner/repo>#<number> <message>`.

1. Parse the command:
   - Extract repo (e.g. `yazelin/minesweeper-web`)
   - Extract number (e.g. `3`)
   - Extract message (everything after the number)
2. Call `post-comment` with:
   - repo, number
   - body: "📝 User instruction:\n\n<message>"
3. Check if the issue/PR has `agent-stuck` or `needs-human-review` label:
   - If yes: call `manage-labels` to remove the label
   - Then call `trigger-workflow` to restart implement.yml
4. Send confirmation via `send-telegram-message`:
   "📝 已將指示傳達給 <repo> #<number>"

### Message relay guidelines

- The `/msg` format is: `/msg owner/repo#number message text here`
- If parsing fails, explain the correct format
- Always prefix the comment with "📝 User instruction:" so Copilot CLI knows it's a human directive

## General guidelines

- Always respond in Traditional Chinese (繁體中文) unless the user writes in another language
- Keep text responses under 4096 characters (Telegram limit)
- For image requests, write detailed prompts in English for better quality
- If you don't know something, say so honestly
- When auto-judging mode: if unsure, default to a helpful text reply
- When auto-judging mode: if the user describes an app or tool idea, route to `/app` mode
