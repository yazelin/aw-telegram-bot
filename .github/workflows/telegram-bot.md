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

secrets:
  TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}

timeout-minutes: 5
---

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
