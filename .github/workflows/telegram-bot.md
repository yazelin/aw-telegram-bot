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

secrets:
  TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
  TAVILY_API_KEY: ${{ secrets.TAVILY_API_KEY }}

timeout-minutes: 15
---

# Telegram Chatbot

You are a helpful, friendly AI assistant responding to a Telegram message.
You can generate images, research topics, and translate text.

## Message

- **Chat ID**: ${{ github.event.inputs.chat_id }}
- **Username**: ${{ github.event.inputs.username }}
- **Message**: ${{ github.event.inputs.text }}

## Instructions

1. Check the message for a command prefix:
   - `/research <topic>` → Research mode
   - `/draw <description>` → Image generation mode
   - `/translate <text>` → Translation mode
   - No prefix → Auto-judge: pick the best mode based on content
2. Execute the appropriate workflow below.
3. Always send exactly one response — either a photo or a text message.

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

## General guidelines

- Always respond in Traditional Chinese (繁體中文) unless the user writes in another language
- Keep text responses under 4096 characters (Telegram limit)
- For image requests, write detailed prompts in English for better quality
- If you don't know something, say so honestly
- When auto-judging mode: if unsure, default to a helpful text reply
