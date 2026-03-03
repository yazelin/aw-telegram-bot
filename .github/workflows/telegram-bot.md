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
3. Send your response back via the Telegram Bot API.

Use the `web-fetch` tool to POST to:

```
https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/sendMessage
```

With this JSON body:

```json
{
  "chat_id": <Chat ID from above>,
  "text": "<your response>",
  "parse_mode": "HTML"
}
```

Replace `<TELEGRAM_BOT_TOKEN>` with the value from the `TELEGRAM_BOT_TOKEN` secret.

## Guidelines

- Keep responses under 4096 characters (Telegram limit).
- If the user asks a programming question, include code examples.
- If you don't know something, say so honestly.
- Respond in the same language the user writes in.
