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
3. Register webhook: visit `https://<worker-url>/register?token=<your-TELEGRAM_SECRET>`
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
