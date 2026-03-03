# aw-telegram-bot Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a personal Telegram chatbot powered by GitHub Copilot (via gh-aw), with a Cloudflare Worker relaying webhooks to GitHub Actions.

**Architecture:** Telegram webhook → Cloudflare Worker (validates & relays) → GitHub repository_dispatch → gh-aw workflow (Copilot engine processes message, replies via Telegram API). The gh-aw workflow IS the chatbot — Copilot receives the user's message as context and uses `web-fetch` to send the reply back.

**Tech Stack:** gh-aw (GitHub Agentic Workflows), Cloudflare Workers (JavaScript/Wrangler), Telegram Bot API, GitHub repository_dispatch API

---

### Task 1: Initialize project and git repo

**Files:**
- Create: `aw-telegram-bot/.gitignore`
- Create: `aw-telegram-bot/README.md`

**Step 1: Initialize git repo**

```bash
cd /home/ct/gh-aw/aw-telegram-bot
git init
```

**Step 2: Create .gitignore**

```gitignore
node_modules/
.wrangler/
.dev.vars
*.log
__pycache__/
.env
```

**Step 3: Create minimal README**

```markdown
# aw-telegram-bot

Personal Telegram chatbot powered by GitHub Copilot via gh-aw.

## Architecture

Telegram → Cloudflare Worker → GitHub Actions (gh-aw) → Telegram reply
```

**Step 4: Initial commit**

```bash
git add .gitignore README.md
git commit -m "chore: init project"
```

---

### Task 2: Create the Cloudflare Worker — project scaffold

**Files:**
- Create: `worker/wrangler.toml`
- Create: `worker/src/index.js`
- Create: `worker/package.json`

**Step 1: Create worker directory and package.json**

```bash
mkdir -p worker/src
```

```json
{
  "name": "telegram-github-relay",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "wrangler dev",
    "deploy": "wrangler deploy"
  },
  "devDependencies": {
    "wrangler": "^4"
  }
}
```

**Step 2: Create wrangler.toml**

```toml
name = "telegram-github-relay"
main = "src/index.js"
compatibility_date = "2024-01-01"
```

Note: Secrets (`TELEGRAM_SECRET`, `GITHUB_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPO`, `TELEGRAM_BOT_TOKEN`) are set via `wrangler secret put <NAME>` at deploy time, NOT in this file.

**Step 3: Create index.js with full Worker logic**

```javascript
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === "/webhook" && request.method === "POST") {
      return handleWebhook(request, env, ctx);
    }

    if (url.pathname === "/register") {
      return registerWebhook(url, env);
    }

    return new Response("aw-telegram-bot relay", { status: 200 });
  },
};

async function handleWebhook(request, env, ctx) {
  // Validate Telegram secret token
  const secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token");
  if (secret !== env.TELEGRAM_SECRET) {
    return new Response("Unauthorized", { status: 403 });
  }

  const update = await request.json();

  // Only process text messages
  if (!update.message?.text) {
    return new Response("OK", { status: 200 });
  }

  // Fire-and-forget: dispatch to GitHub
  ctx.waitUntil(dispatchToGitHub(update, env));

  return new Response("OK", { status: 200 });
}

async function dispatchToGitHub(update, env) {
  const msg = update.message;

  const response = await fetch(
    `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/dispatches`,
    {
      method: "POST",
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "aw-telegram-bot",
      },
      body: JSON.stringify({
        event_type: "telegram_message",
        client_payload: {
          chat_id: msg.chat.id,
          text: msg.text,
          username: msg.from?.username || "",
          message_id: msg.message_id,
        },
      }),
    }
  );

  if (!response.ok) {
    console.error("GitHub dispatch failed:", response.status, await response.text());
  }
}

async function registerWebhook(requestUrl, env) {
  const webhookUrl = `${requestUrl.protocol}//${requestUrl.hostname}/webhook`;
  const result = await fetch(
    `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/setWebhook`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: webhookUrl,
        secret_token: env.TELEGRAM_SECRET,
        allowed_updates: ["message"],
        drop_pending_updates: true,
      }),
    }
  );

  const json = await result.json();
  return new Response(JSON.stringify(json, null, 2), {
    headers: { "Content-Type": "application/json" },
  });
}
```

**Step 4: Install dependencies**

```bash
cd worker && npm install && cd ..
```

**Step 5: Commit**

```bash
git add worker/
git commit -m "feat: add Cloudflare Worker relay"
```

---

### Task 3: Create the gh-aw workflow

**Files:**
- Create: `.github/workflows/telegram-bot.md`

**Step 1: Create workflow directory**

```bash
mkdir -p .github/workflows
```

**Step 2: Create the gh-aw workflow markdown**

```markdown
---
description: |
  Telegram chatbot powered by Copilot. Receives messages via repository_dispatch
  from Cloudflare Worker relay, generates a response, and replies via Telegram API.

on: api dispatch telegram_message

engine: copilot

permissions:
  contents: read

network: defaults

tools:
  web-fetch:

secrets:
  TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}

timeout-minutes: 5
---

# Telegram Chatbot

You are a helpful, friendly AI assistant responding to a Telegram message.

## Message Context

- **Chat ID**: ${{ github.event.client_payload.chat_id }}
- **Username**: ${{ github.event.client_payload.username }}
- **Message**: ${{ github.event.client_payload.text }}

## Instructions

1. Read the user's message above.
2. Generate a helpful, concise response. Be conversational and friendly.
3. Send your response back to the user via the Telegram Bot API.

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
```

**Step 3: Compile the workflow (requires gh-aw CLI)**

```bash
gh aw compile
```

Note: If `gh aw` is not installed, install it first:

```bash
gh extension install github/gh-aw
```

**Step 4: Commit**

```bash
git add .github/
git commit -m "feat: add gh-aw telegram chatbot workflow"
```

---

### Task 4: Create setup and deployment scripts

**Files:**
- Create: `scripts/setup.sh`

**Step 1: Create scripts directory**

```bash
mkdir -p scripts
```

**Step 2: Create setup script**

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== aw-telegram-bot Setup ==="
echo ""

# Check prerequisites
command -v wrangler >/dev/null 2>&1 || { echo "Error: wrangler not found. Run: npm i -g wrangler"; exit 1; }
command -v gh >/dev/null 2>&1 || { echo "Error: gh CLI not found."; exit 1; }

echo "Step 1: Set Cloudflare Worker secrets"
echo "You will be prompted for each secret value."
echo ""

cd worker

echo "--- TELEGRAM_BOT_TOKEN (from @BotFather) ---"
wrangler secret put TELEGRAM_BOT_TOKEN

echo "--- TELEGRAM_SECRET (any random string for webhook validation) ---"
wrangler secret put TELEGRAM_SECRET

echo "--- GITHUB_TOKEN (fine-grained PAT with contents:write on this repo) ---"
wrangler secret put GITHUB_TOKEN

echo "--- GITHUB_OWNER (GitHub username or org) ---"
wrangler secret put GITHUB_OWNER

echo "--- GITHUB_REPO (repository name) ---"
wrangler secret put GITHUB_REPO

echo ""
echo "Step 2: Deploy Cloudflare Worker"
wrangler deploy

echo ""
echo "Step 3: Register Telegram webhook"
WORKER_URL=$(wrangler whoami 2>/dev/null | grep -oP 'https://[^ ]+' || echo "https://telegram-github-relay.<your-subdomain>.workers.dev")
echo "Visit this URL to register the webhook:"
echo "  ${WORKER_URL}/register"
echo ""
echo "Or run:"
echo "  curl ${WORKER_URL}/register"

cd ..

echo ""
echo "Step 4: Set GitHub repo secrets"
echo "Go to your repo Settings > Secrets and add:"
echo "  TELEGRAM_BOT_TOKEN = your bot token from @BotFather"
echo ""
echo "Step 5: Compile and push gh-aw workflow"
echo "  gh aw compile"
echo "  git add . && git push"
echo ""
echo "=== Setup complete! ==="
```

**Step 3: Make executable and commit**

```bash
chmod +x scripts/setup.sh
git add scripts/
git commit -m "feat: add setup script"
```

---

### Task 5: Update README with full documentation

**Files:**
- Modify: `README.md`

**Step 1: Write comprehensive README**

```markdown
# aw-telegram-bot

Personal Telegram chatbot powered by GitHub Copilot via [gh-aw](https://github.com/github/gh-aw) (GitHub Agentic Workflows).

## Architecture

```
Telegram → Cloudflare Worker → GitHub Actions (gh-aw + Copilot) → Telegram reply
```

1. You send a message to the Telegram bot
2. Cloudflare Worker receives the webhook, validates it, and triggers a GitHub `repository_dispatch`
3. gh-aw workflow runs with Copilot as the AI engine
4. Copilot generates a response and sends it back via Telegram API

## Prerequisites

- [GitHub CLI](https://cli.github.com/) with [gh-aw extension](https://github.com/github/gh-aw)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/) (Cloudflare Workers)
- A [Telegram Bot](https://core.telegram.org/bots#botfather) (create via @BotFather)
- GitHub Copilot subscription
- A GitHub repo to host the workflow

## Setup

```bash
./scripts/setup.sh
```

Or manually:

1. Deploy the Cloudflare Worker: `cd worker && wrangler deploy`
2. Set Worker secrets: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_SECRET`, `GITHUB_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPO`
3. Register webhook: visit `https://<worker-url>/register`
4. Set GitHub repo secret: `TELEGRAM_BOT_TOKEN`
5. Compile workflow: `gh aw compile`
6. Push to GitHub

## Project Structure

```
├── worker/              # Cloudflare Worker (webhook relay)
│   ├── src/index.js
│   ├── wrangler.toml
│   └── package.json
├── .github/workflows/   # gh-aw workflow
│   └── telegram-bot.md
├── scripts/
│   └── setup.sh
└── README.md
```

## License

MIT
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add full README"
```

---

### Task 6: End-to-end testing

**Files:** None (manual testing)

**Step 1: Verify Cloudflare Worker is deployed**

```bash
cd worker && wrangler deploy
```

Visit the worker URL in browser — should see "aw-telegram-bot relay".

**Step 2: Register Telegram webhook**

```bash
curl https://<your-worker>.workers.dev/register
```

Expected: `{"ok": true, "result": true, "description": "Webhook was set"}`

**Step 3: Verify gh-aw workflow is compiled and pushed**

```bash
gh aw compile
git add .github/
git push
```

Check that `.github/workflows/telegram-bot.lock.yml` exists.

**Step 4: Send a test message**

Send any message to your Telegram bot. Check:
1. GitHub Actions tab — a new workflow run should appear
2. The workflow should complete successfully
3. You should receive a reply in Telegram

**Step 5: Troubleshoot if needed**

- Check Worker logs: `cd worker && wrangler tail`
- Check GitHub Actions logs in the repo
- Verify all secrets are set correctly

**Step 6: Final commit if any fixes were needed**

```bash
git add -A && git commit -m "fix: adjustments from e2e testing"
```
