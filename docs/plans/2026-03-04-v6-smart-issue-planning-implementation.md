# Smart Issue Planning Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Modify the App Factory prompt so the parent repo's Copilot agent creates fewer, larger, verifiable issues instead of 5-8 tiny ones.

**Architecture:** Only change `telegram-bot.md` Phase 2-4 and App Factory guidelines. No Python, no workflow YAML, no child repo changes. The AI agent gets better instructions for planning; everything downstream stays the same.

**Tech Stack:** gh-aw prompt markdown

---

### Task 1: Replace Phase 2 (Deep Research)

**Files:**
- Modify: `.github/workflows/telegram-bot.md:561-564`

**Step 1: Replace Phase 2 content**

Find this text (lines 561-564):
```markdown
### Phase 2: Search for existing solutions

1. Use `web-search` to find relevant open-source projects or libraries
2. Decide: build from scratch, reference an existing project, or suggest a fork
```

Replace with:
```markdown
### Phase 2: Deep Research (Diverge)

1. Use `web-search` to find 2-3 similar open-source projects
2. Use `web-fetch` to read their README and file structure
3. Extract: typical modules, file organization, feature breakdown
4. Note which features are tightly coupled vs independent
5. Decide: build from scratch, reference an existing project, or suggest a fork
```

**Step 2: Verify**

Run: `grep -n "Deep Research" .github/workflows/telegram-bot.md`
Expected: line ~561 shows `### Phase 2: Deep Research (Diverge)`

**Step 3: Commit**

```bash
git add .github/workflows/telegram-bot.md
git commit -m "prompt: Phase 2 deep research with web-fetch"
```

---

### Task 2: Expand Phase 3 (Define Done)

**Files:**
- Modify: `.github/workflows/telegram-bot.md:566-578`

**Step 1: Add acceptance criteria block after tech stack decisions**

Find this text (lines 566-578):
```markdown
### Phase 3: Technical decisions (MVP principles)

Apply these rules strictly:
- Static over backend (use GitHub Pages if possible)
- Native over framework (pure HTML/CSS/JS over React/Vue)
- localStorage over database
- Zero dependencies preferred
- Fewer dependencies = higher chance of Copilot CLI success

Determine:
- **Repo name**: lowercase, hyphenated (e.g. `minesweeper-web`)
- **Tech stack**: specific languages, frameworks (or lack thereof)
- **Deploy target**: GitHub Pages / repo only / Cloudflare Workers
```

Replace with:
```markdown
### Phase 3: Technical decisions + Define "done"

Apply these rules strictly:
- Static over backend (use GitHub Pages if possible)
- Native over framework (pure HTML/CSS/JS over React/Vue)
- localStorage over database
- Zero dependencies preferred
- Fewer dependencies = higher chance of Copilot CLI success

Determine:
- **Repo name**: lowercase, hyphenated (e.g. `minesweeper-web`)
- **Tech stack**: specific languages, frameworks (or lack thereof)
- **Deploy target**: GitHub Pages / repo only / Cloudflare Workers

Write **whole-app acceptance criteria** — a numbered list of user-visible outcomes that define "done" for the entire app. Example:
```
1. User can play a complete round of the guessing game
2. Game provides correct high/low feedback
3. Round ends on correct guess or attempt exhaustion
4. Best score persists across browser sessions
5. App is deployed and accessible via GitHub Pages
```
These become the "Global Acceptance Criteria" section in AGENTS.md.
```

**Step 2: Verify**

Run: `grep -n "Define.*done" .github/workflows/telegram-bot.md`
Expected: line ~566 shows `### Phase 3: Technical decisions + Define "done"`

**Step 3: Commit**

```bash
git add .github/workflows/telegram-bot.md
git commit -m "prompt: Phase 3 add whole-app acceptance criteria"
```

---

### Task 3: Rewrite Phase 4 (Plan Backwards)

**Files:**
- Modify: `.github/workflows/telegram-bot.md:580-598`

**Step 1: Replace Phase 4 content**

Find this text (lines 580-598, after Task 2 changes line numbers will have shifted):
```markdown
### Phase 4: Plan content

Write these in your mind (do NOT output them to chat):

1. **README.md**: Project title, description, tech stack, how to run locally, deploy info
2. **AGENTS.md**: Full project spec including:
   - Project goal
   - Tech stack with specific versions/choices
   - Architecture overview
   - References to open-source projects (if any)
   - Package usage principles
   - Acceptance criteria for the whole project
3. **Issue list**: 3-8 issues, each with:
   - Clear title
   - Detailed body with acceptance criteria
   - Ordered by implementation dependency (foundational first)
4. **Skills selection**: Pick from available templates:
   - Always include: `issue-workflow`, `code-standards`, `testing`
   - If deploying to Pages: include `deploy-pages`
```

Replace with:
```markdown
### Phase 4: Plan backwards (Converge)

Write these in your mind (do NOT output them to chat):

1. **README.md**: Project title, description, tech stack, how to run locally, deploy info
2. **AGENTS.md**: Full project spec including:
   - Project goal
   - Tech stack with specific versions/choices
   - Architecture overview
   - References to open-source projects (if any)
   - Package usage principles
   - Global Acceptance Criteria (from Phase 3)
3. **Issue list** — plan backwards from acceptance criteria:
   a. List all features needed to meet the acceptance criteria
   b. Map dependencies: if A depends on B, mark them as coupled
   c. Merge tightly-coupled features into single issues
   d. Target 2-5 issues total, each a meaningful functional module
   e. Each issue body must include:
      - **Objective**: what this delivers in user-visible terms
      - **Steps**: step-by-step checklist (Copilot commits per step)
      - **Files**: which files to create/modify
      - **Validation**: how to verify it works after completion
4. **Skills selection**: Pick from available templates:
   - Always include: `issue-workflow`, `code-standards`, `testing`
   - If deploying to Pages: include `deploy-pages`
```

**Step 2: Verify**

Run: `grep -n "Plan backwards" .github/workflows/telegram-bot.md`
Expected: shows `### Phase 4: Plan backwards (Converge)`

**Step 3: Commit**

```bash
git add .github/workflows/telegram-bot.md
git commit -m "prompt: Phase 4 dependency-aware issue planning"
```

---

### Task 4: Update App Factory guidelines

**Files:**
- Modify: `.github/workflows/telegram-bot.md:620-630`

**Step 1: Replace guidelines**

Find this text (line numbers will have shifted from previous edits):
```markdown
### App Factory guidelines

- Repo names should be descriptive and short (2-4 words, hyphenated)
- README should be in the user's language (Traditional Chinese)
- AGENTS.md should be in English (Copilot CLI works better in English)
- Issues should be in English with clear acceptance criteria
- Each issue should be independently implementable when possible
- **Each issue must be small enough for Copilot CLI to complete in under 45 minutes**
- Prefer more smaller issues (5-8) over fewer large ones (2-3)
- First issue should set up the project skeleton
- Last issue should handle deployment (if applicable)
```

Replace with:
```markdown
### App Factory guidelines

- Repo names should be descriptive and short (2-4 words, hyphenated)
- README should be in the user's language (Traditional Chinese)
- AGENTS.md should be in English (Copilot CLI works better in English)
- Issues should be in English with clear acceptance criteria
- Target 2-5 issues based on dependency analysis
- Merge tightly-coupled features into one issue
- Keep independent features as separate issues
- Each issue should represent a verifiable functional module
- Include a step-by-step checklist and validation section in each issue
- Each issue should be completable by Copilot CLI within the 55-minute timeout
- First issue should include the project skeleton + core functionality
- Last issue should handle deployment and final polish (if applicable)
```

**Step 2: Verify**

Run: `grep -n "2-5 issues" .github/workflows/telegram-bot.md`
Expected: shows `- Target 2-5 issues based on dependency analysis`

Run: `grep -n "5-8" .github/workflows/telegram-bot.md`
Expected: no matches (old guideline removed)

**Step 3: Commit**

```bash
git add .github/workflows/telegram-bot.md
git commit -m "prompt: update guidelines for fewer, larger issues"
```

---

### Task 5: Compile and push

**Step 1: Compile**

Run: `gh aw compile`
Expected: telegram-bot.lock.yml updated

**Step 2: Commit compiled output**

```bash
git add .github/workflows/telegram-bot.lock.yml
git commit -m "chore: gh aw compile after prompt changes"
```

**Step 3: Push**

```bash
git push
```

**Step 4: Verify**

Run: `grep -c "5-8" .github/workflows/telegram-bot.md`
Expected: 0

Run: `grep -c "2-5 issues" .github/workflows/telegram-bot.md`
Expected: 1

Run: `grep -c "Deep Research" .github/workflows/telegram-bot.md`
Expected: 1

Run: `grep -c "Plan backwards" .github/workflows/telegram-bot.md`
Expected: 1
