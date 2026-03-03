# v3 Research Mode + Command Routing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add research/investigation capability and prefix-based command routing (/research, /draw, /translate) to the Telegram bot.

**Architecture:** Single workflow. Tavily MCP (remote HTTP) + built-in web-search + web-fetch for research. Agent reads message prefix to route to the correct mode, or auto-judges when no prefix. All changes are in one file: `.github/workflows/telegram-bot.md`.

**Tech Stack:** gh-aw, Copilot (gpt-5.3-codex), Tavily MCP (remote HTTP), nanobanana-py (unchanged), Python safe-inputs (unchanged)

---

### Task 1: Add Tavily MCP server and web-search tool to frontmatter

**Files:**
- Modify: `.github/workflows/telegram-bot.md:26-47` (network, tools, mcp-servers sections)

**Step 1: Add `mcp.tavily.com` to network allowlist**

In `.github/workflows/telegram-bot.md`, change lines 26-30 from:

```yaml
network:
  allowed:
    - defaults
    - api.telegram.org
    - generativelanguage.googleapis.com
```

To:

```yaml
network:
  allowed:
    - defaults
    - api.telegram.org
    - generativelanguage.googleapis.com
    - mcp.tavily.com
```

**Step 2: Add `web-search:` to tools**

Change lines 32-33 from:

```yaml
tools:
  web-fetch:
```

To:

```yaml
tools:
  web-fetch:
  web-search:
```

**Step 3: Add Tavily MCP server**

After the existing `nanobanana:` mcp-server block (after line 47), add:

```yaml
  tavily:
    url: "https://mcp.tavily.com/mcp/?tavilyApiKey=${{ secrets.TAVILY_API_KEY }}"
    allowed: ["*"]
```

**Step 4: Compile and verify**

```bash
cd /home/ct/gh-aw/aw-telegram-bot
gh aw compile
```

Expected: 0 errors. Check that `.github/workflows/telegram-bot.lock.yml` now contains the tavily MCP server config.

**Step 5: Commit**

```bash
git add .github/workflows/telegram-bot.md .github/workflows/telegram-bot.lock.yml
git commit -m "feat: add Tavily MCP server and web-search tool"
```

---

### Task 2: Add TAVILY_API_KEY to secrets section and increase timeout

**Files:**
- Modify: `.github/workflows/telegram-bot.md:115-119` (secrets and timeout sections)

**Step 1: Add TAVILY_API_KEY to secrets**

Change:

```yaml
secrets:
  TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

To:

```yaml
secrets:
  TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
  TAVILY_API_KEY: ${{ secrets.TAVILY_API_KEY }}
```

**Step 2: Increase timeout from 5 to 15 minutes**

Change:

```yaml
timeout-minutes: 5
```

To:

```yaml
timeout-minutes: 15
```

**Step 3: Compile and verify**

```bash
gh aw compile
```

Expected: 0 errors.

**Step 4: Commit**

```bash
git add .github/workflows/telegram-bot.md .github/workflows/telegram-bot.lock.yml
git commit -m "feat: add TAVILY_API_KEY secret and increase timeout to 15 min"
```

---

### Task 3: Update prompt for command routing and research workflow

**Files:**
- Modify: `.github/workflows/telegram-bot.md:121-158` (prompt body after `---`)

**Step 1: Replace the entire prompt body**

Replace everything after the closing `---` of frontmatter (line 121 onwards) with:

```markdown
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

- Keep text responses under 4096 characters (Telegram limit)
- For image requests, write detailed prompts in English for better quality
- Respond in the same language the user writes in
- If you don't know something, say so honestly
- When auto-judging mode: if unsure, default to a helpful text reply
```

**Step 2: Compile and verify**

```bash
gh aw compile
```

Expected: 0 errors.

**Step 3: Commit**

```bash
git add .github/workflows/telegram-bot.md .github/workflows/telegram-bot.lock.yml
git commit -m "feat: update prompt for command routing and research workflow"
```

---

### Task 4: Push and test all three modes

**Step 1: Push all changes**

```bash
git push
```

**Step 2: Test text message (regression)**

Send to Telegram bot: `你好`

Expected: Bot replies with a friendly text message (same as v1/v2).

**Step 3: Test image generation (regression)**

Send to Telegram bot: `/draw 一隻穿太空衣的貓`

Expected: Bot sends back a photo with a caption (~2 min).

**Step 4: Test research mode**

Send to Telegram bot: `/research 2026年台灣半導體產業最新發展`

Expected: Bot sends back a structured research report with summary, key findings, and source links (~2-3 min).

**Step 5: Test translation mode**

Send to Telegram bot: `/translate Hello, how are you today?`

Expected: Bot sends back a Chinese translation.

**Step 6: Test auto-judge (no prefix)**

Send to Telegram bot: `最近有什麼科技新聞？`

Expected: Bot auto-judges this as needing research and sends back a report with sources.

**Step 7: Check workflow logs if any test fails**

```bash
gh run list --repo yazelin/aw-telegram-bot --limit 5
gh run view <RUN_ID> --repo yazelin/aw-telegram-bot --log 2>&1 | grep -i "tavily\|web.search\|research\|error\|fail" | head -30
```

Possible failure points:
- Tavily MCP connection fails → check network allowlist for `mcp.tavily.com`
- Tavily auth fails → verify `TAVILY_API_KEY` secret is set correctly
- web-search not available → check `tools:` section in compiled lock.yml
- Timeout → check if 15 minutes is enough; consider increasing if needed
- Agent doesn't recognize prefix → check prompt wording

**Step 8: Commit any fixes if needed**

```bash
git add .github/workflows/telegram-bot.md .github/workflows/telegram-bot.lock.yml
git commit -m "fix: adjust v3 config based on testing"
git push
```

---

### Task 5: Create v3 branch and tag

After all tests pass:

**Step 1: Tag the current state**

```bash
git tag v3-research-mode
git push origin v3-research-mode
```

**Step 2: Create a preservation branch**

```bash
git checkout -b v3-research-mode
git push origin refs/heads/v3-research-mode:refs/heads/v3-research-mode
git checkout main
```

---

### Troubleshooting Reference

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Tavily MCP init fails | Network blocked | Add `mcp.tavily.com` to `network.allowed` |
| Tavily auth error | Wrong API key | Verify `TAVILY_API_KEY` secret value |
| `web-search` tool not found | Not in `tools:` section | Add `web-search:` under `tools:` |
| Agent ignores prefix | Prompt not clear enough | Strengthen prefix routing instructions |
| Research report too long | Too many sources fetched | Add "limit to 3-5 sources" in prompt |
| Research takes >15 min | Too many web-fetch calls | Reduce source limit or increase timeout |
| Image generation broke | nanobanana config changed | Verify mcp-servers section unchanged |
| Compile error after adding tavily | YAML syntax issue | Check indentation; `url:` must be under `tavily:` |
