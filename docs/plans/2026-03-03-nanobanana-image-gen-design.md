# aw-telegram-bot v2: Image Generation via nanobanana-py

## Goal

Let Telegram users request AI-generated images via text descriptions. Copilot agent judges whether a message is an image request, calls nanobanana-py MCP server to generate the image, and sends it back to Telegram as a photo.

## Architecture

```
User sends "畫一隻穿太空衣的貓"
  │
  ▼
Telegram → CF Worker → GitHub Actions (workflow_dispatch)
  │
  ▼
gh-aw Agent (Copilot gpt-5.3-codex)
  │
  ├─ Judges: this is an image request
  │  Calls nanobanana MCP tool: generate_image(prompt)
  │
  ▼
nanobanana-py MCP Server (on runner)
  ├─ Calls Gemini API to generate image
  └─ Saves to /tmp/nanobanana-output/image.png
  │  Returns file path to agent
  ▼
Agent gets path "/tmp/nanobanana-output/image.png"
  │  Calls safe-inputs: send-telegram-photo(chat_id, photo_path, caption)
  ▼
safe-inputs handler (Python)
  ├─ Reads image file
  └─ multipart POST to Telegram sendPhoto API
  │
  ▼
User receives cat in spacesuit 🐱🚀
```

## Scope

### In scope (v2)
- `generate_image` only (text-to-image)
- nanobanana-py as MCP server via `mcp-servers:` frontmatter
- `send-telegram-photo` safe-inputs tool (multipart/form-data upload)
- Agent prompt updated to judge text vs image requests
- New secret: `GEMINI_API_KEY`
- Network allowlist: `generativelanguage.googleapis.com`

### Out of scope (future v3)
- edit_image, restore_image (requires image upload from user)
- Image upload from Telegram (Worker changes to handle photo messages)
- Reply context (reply_to_message text/photo passthrough)
- Other nanobanana tools (icon, pattern, story, diagram)

## Components

### 1. Workflow frontmatter changes

```yaml
mcp-servers:
  - name: nanobanana
    command: uvx
    args: [nanobanana-py]
    env:
      NANOBANANA_GEMINI_API_KEY: "${{ secrets.GEMINI_API_KEY }}"
      NANOBANANA_OUTPUT_DIR: "/tmp/nanobanana-output"
    allowed: [generate_image]

network:
  allowed:
    - defaults
    - api.telegram.org
    - generativelanguage.googleapis.com

safe-inputs:
  send-telegram-photo:
    description: "Send a photo to a Telegram chat"
    inputs:
      chat_id: { type: string, required: true }
      photo_path: { type: string, required: true }
      caption: { type: string, required: false }
    py: |
      # multipart/form-data upload to Telegram sendPhoto API
      # reads file from photo_path, uploads as binary
    env:
      TELEGRAM_BOT_TOKEN: "${{ secrets.TELEGRAM_BOT_TOKEN }}"
```

### 2. Prompt changes

Agent instructions updated to:
- Judge if message is an image request
- If yes: call generate_image → get file path → call send-telegram-photo
- If no: call send-telegram-message (existing)
- On failure: fall back to text message explaining the error

### 3. Secrets

New GitHub repo secret:
- `GEMINI_API_KEY` — Google Gemini API key for nanobanana-py

### 4. No CF Worker changes

Worker remains unchanged — still only handles text messages via workflow_dispatch.

## Key risks

| Risk | Mitigation |
|------|-----------|
| MCP server can't reach Gemini API (firewall) | Add `generativelanguage.googleapis.com` to allowlist |
| File path mismatch between MCP and safe-inputs | Use shared /tmp directory |
| `uvx nanobanana-py` not available on runner | gh-aw runners should have uv/uvx; fall back to pip install |
| Image generation timeout (>60s) | Set safe-inputs timeout to 120s; nanobanana has own timeout config |
| Telegram photo size limit (10MB) | nanobanana default 1K resolution should be well under |

## Decision log

- **Approach B chosen**: MCP server + safe-inputs split (over all-in-one safe-inputs)
- **Python handler**: Proven working from v1; JS handler had issues
- **generate_image only**: edit/restore requires image upload which isn't supported yet
- **/tmp shared dir**: Simplest file sharing between MCP server and safe-inputs
