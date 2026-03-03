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
echo "  ${WORKER_URL}/register?token=<your-TELEGRAM_SECRET>"
echo ""
echo "Or run:"
echo "  curl '${WORKER_URL}/register?token=<your-TELEGRAM_SECRET>'"

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
