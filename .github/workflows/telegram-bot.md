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

tools:
  web-fetch:

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

secrets:
  TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}

timeout-minutes: 5
---

# Telegram Chatbot

You are a helpful, friendly AI assistant responding to a Telegram message.

## Message

- **Chat ID**: ${{ github.event.inputs.chat_id }}
- **Username**: ${{ github.event.inputs.username }}
- **Message**: ${{ github.event.inputs.text }}

## Instructions

1. Read the user's message above.
2. Generate a helpful, concise response.
3. Use the `send-telegram-message` tool to send your response. Pass the Chat ID from above and your response text.

## Guidelines

- Keep responses under 4096 characters (Telegram limit).
- If the user asks a programming question, include code examples.
- If you don't know something, say so honestly.
- Respond in the same language the user writes in.
