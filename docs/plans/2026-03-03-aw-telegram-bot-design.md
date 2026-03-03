# aw-telegram-bot Design

## Overview

A personal Telegram chatbot powered by GitHub Copilot SDK (GPT 5 mini), running on GitHub Actions via gh-aw (GitHub Agentic Workflows). A Cloudflare Worker acts as the webhook relay between Telegram and GitHub Actions.

## Architecture

```
[Telegram User]
      | sends message
      v
[Telegram API] -> Webhook POST
      |
      v
[Cloudflare Worker]
  - Validates webhook secret
  - Extracts message content + chat_id
  - Sends repository_dispatch to GitHub
  - Returns 200 immediately
      |
      v
[GitHub Actions - gh-aw workflow]
  - Triggered by repository_dispatch (type: telegram_message)
  - Reads event payload (chat_id, message_text)
  - Initializes Copilot SDK client (OAuth)
  - Sends message to Copilot, gets response
  - Replies via Telegram Bot API
      |
      v
[Telegram User] <- receives reply
```

## Components

### 1. Cloudflare Worker (JavaScript)

- Receives Telegram webhook POST requests
- Validates the secret token header
- Sends `repository_dispatch` event to GitHub via API
- Returns 200 immediately to avoid Telegram timeout
- Minimal logic, just a relay

### 2. gh-aw Workflow (Markdown + Python)

- Trigger: `repository_dispatch` with type `telegram_message`
- Payload contains `chat_id` and `message_text`
- Python handler script:
  - Initializes Copilot SDK with GitHub token
  - Sends user message, receives AI response
  - Calls Telegram Bot API to send reply
- Uses gh-aw for natural language workflow definition

### 3. Python Bot Handler

- Uses `github-copilot-sdk` for AI inference
- Uses `requests` or `httpx` for Telegram Bot API calls
- Stateless per invocation (no session persistence initially)

## Authentication & Secrets

| Secret | Purpose | Where Used |
|--------|---------|------------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API auth | GitHub Actions |
| `TELEGRAM_WEBHOOK_SECRET` | Validate webhook origin | CF Worker + Telegram setup |
| `GITHUB_TOKEN` | Auto-provided, Copilot SDK auth | GitHub Actions |
| `CF_WORKER_GITHUB_TOKEN` | Trigger repository_dispatch | CF Worker |

## Project Structure

```
aw-telegram-bot/
├── worker/                  # Cloudflare Worker
│   ├── index.js
│   └── wrangler.toml
├── .github/
│   └── workflows/
│       └── telegram-bot.yml  # gh-aw workflow
├── bot/
│   ├── handler.py           # Message processing logic
│   └── requirements.txt
├── scripts/
│   └── setup-webhook.sh     # Set up Telegram webhook URL
└── README.md
```

## Constraints & Notes

- Single user only (personal use)
- Stateless: no conversation history across messages (MVP)
- Response latency: ~5-15 seconds (Actions cold start + Copilot inference)
- GitHub Actions free tier: 2,000 minutes/month (sufficient for personal use)
- Cloudflare Workers free tier: 100,000 requests/day (more than enough)
- Copilot SDK requires GitHub Copilot subscription

## Future Enhancements (not in MVP)

- Conversation history (store in GitHub repo or KV)
- Rich message formatting (markdown, code blocks)
- Command routing (/ask, /code, /explain)
- Rate limiting
