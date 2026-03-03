# aw-telegram-bot v3: Research Mode + Command Routing

## Goal

Add research/investigation capability to the Telegram bot via Tavily MCP + web-search + web-fetch, and introduce prefix-based command routing so users can explicitly choose modes (/research, /draw, /translate) or let the agent auto-judge.

## Architecture

```
使用者：「/research 台灣半導體產業的最新發展」
  │
  ▼
Telegram → CF Worker → GitHub Actions (workflow_dispatch)
  │
  ▼
Copilot Agent（判斷：/research 前綴 → 研究模式）
  │
  ├─ 1. Tavily MCP: search(query)       ← 結構化搜尋結果
  ├─ 2. web-search(query)               ← 補充搜尋角度
  ├─ 3. web-fetch(url) × 2-3            ← 深入讀取重要來源
  │
  ▼
Agent 綜合所有結果，整理成報告
  │  呼叫 send-telegram-message(chat_id, text)
  ▼
使用者收到研究報告（含來源連結）
```

## Scope

### In scope (v3)

- Tavily MCP server (remote HTTP, no Docker)
- Built-in `web-search:` tool
- Prefix-based command routing: `/research`, `/draw`, `/translate`
- Agent auto-judgment for messages without prefix
- Updated prompt with multi-mode instructions
- `timeout-minutes` increased from 5 to 15
- New secret: `TAVILY_API_KEY` (already set)

### Out of scope (future)

- Orchestrator/worker pattern (dispatch-workflow)
- Subagent parallel research
- Image upload from Telegram (photo messages)
- Reply context passthrough
- Deep research mode (>5 sources)

## Command Routing

| Prefix | Mode | Tools |
|--------|------|-------|
| `/research <topic>` | Research | Tavily + web-search + web-fetch |
| `/draw <description>` | Image generation | nanobanana generate_image |
| `/translate <text>` | Translation | None (agent translates directly) |
| No prefix | Auto-judge | Agent picks the best mode based on content |

## Components

### 1. Tavily MCP (remote HTTP)

```yaml
mcp-servers:
  tavily:
    url: "https://mcp.tavily.com/mcp/?tavilyApiKey=${{ secrets.TAVILY_API_KEY }}"
    allowed: ["*"]
```

No Docker container needed. Remote HTTP endpoint, authenticated via URL query parameter.

### 2. Built-in tools

```yaml
tools:
  web-fetch:
  web-search:    # new
```

### 3. Network allowlist

```yaml
network:
  allowed:
    - defaults
    - api.telegram.org
    - generativelanguage.googleapis.com
    - mcp.tavily.com    # new
```

### 4. Secrets

```yaml
secrets:
  TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
  TAVILY_API_KEY: ${{ secrets.TAVILY_API_KEY }}    # new
```

### 5. Timeout

```yaml
timeout-minutes: 15    # was 5
```

### 6. No CF Worker changes

Worker remains unchanged — still handles text messages only via workflow_dispatch.

### 7. No safe-inputs changes

send-telegram-message and send-telegram-photo remain unchanged.

### 8. nanobanana MCP unchanged

Same container mode configuration as v2.

## Prompt Structure

```markdown
## Instructions

1. Check message prefix:
   - `/research <topic>` → Research mode
   - `/draw <description>` → Image generation mode
   - `/translate <text>` → Translation mode
   - No prefix → Auto-judge based on content

## Research workflow

1. Use Tavily search for the topic (advanced depth)
2. Use web-search for additional perspectives
3. Use web-fetch to read 2-3 most important sources
4. Synthesize into a structured report:
   - Summary (3-5 sentences)
   - Key findings (bullet points)
   - Source links
5. Send via send-telegram-message

## Image generation workflow
(unchanged from v2)

## Translation workflow
1. Detect source language
2. Translate to target language (default: Chinese ↔ English)
3. Send via send-telegram-message
```

## Expected Performance

| Mode | Estimated time |
|------|---------------|
| Text reply | ~1-1.5 min |
| Image generation | ~2-2.5 min |
| Research | ~1.5-3 min |
| Translation | ~1-1.5 min |

Research is not significantly slower because Tavily returns structured results directly (no need to crawl/parse).

## Key Risks

| Risk | Mitigation |
|------|-----------|
| Tavily remote MCP connection fails | Fallback to web-search + web-fetch only |
| Research exceeds 15 min timeout | Prompt limits to 3-5 sources max |
| Tavily API quota exceeded | Free tier: 1000 searches/month; monitor usage |
| Agent misroutes (wrong mode) | Prefix commands give explicit control |

## Decision Log

- **Remote HTTP Tavily** over Docker container: simpler config, no volume mount needed, Tavily provides the endpoint
- **Single workflow** over orchestrator/worker: files share /tmp, no sync issues, Actions parallelizes separate messages automatically
- **15 min timeout** over 5 min: research needs more time, well within 360 min max
- **Translation via agent** (no external tool): Copilot/GPT translates well natively
- **Mixed routing** (prefix + auto-judge): explicit when needed, smart when not
