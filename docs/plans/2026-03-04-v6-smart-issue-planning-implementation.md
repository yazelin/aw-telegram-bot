# Smart Issue Planning Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Optimize App Factory end-to-end: smarter issue planning (2-5 issues), structured issue bodies, guided implementation prompts, validation-aware review, and review fallback.

**Architecture:** Changes span 3 areas:
1. Parent repo prompt (`telegram-bot.md`) — smarter planning, remove MVP bias
2. Child repo templates (`implement.yml`, `review.yml`) — better prompts + review fallback
3. No Python script changes — same JSON interfaces

**Tech Stack:** gh-aw prompt markdown, GitHub Actions YAML

**References:**
- agentics (official): `plan.md` issue format (Objective/Context/Approach/Files/Acceptance Criteria), `grumpy-reviewer.md` (must take action), max 5 sub-issues
- Apptopia (保哥): `write-code` skill (7-phase implementation with verification), structured issue templates (MoSCoW + Given/When/Then)

---

### Task 1: Rewrite Phase 2 — Deep Research

**Files:**
- Modify: `.github/workflows/telegram-bot.md:561-564`

**Step 1: Replace Phase 2 content**

Find:
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

**Step 2: Commit**

```bash
git add .github/workflows/telegram-bot.md
git commit -m "prompt: Phase 2 deep research with web-fetch"
```

---

### Task 2: Rewrite Phase 3 — Remove MVP bias, add acceptance criteria

**Files:**
- Modify: `.github/workflows/telegram-bot.md` (Phase 3 section)

**Why:** The title "MVP principles" signals the agent to minimize everything, resulting in trivially small issues. We keep the tech simplicity rules but reframe the purpose.

**Step 1: Replace Phase 3 content**

Find:
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

**Tech simplicity rules** (for Copilot CLI reliability, not for minimizing scope):
- Static over backend (use GitHub Pages if possible)
- Native over framework (pure HTML/CSS/JS over React/Vue)
- localStorage over database
- Zero dependencies preferred
- Fewer dependencies = higher chance of Copilot CLI success

Determine:
- **Repo name**: lowercase, hyphenated (e.g. `minesweeper-web`)
- **Tech stack**: specific languages, frameworks (or lack thereof)
- **Deploy target**: GitHub Pages / repo only / Cloudflare Workers

**Define "done"** — write whole-app acceptance criteria as a numbered list of user-visible outcomes. Example:
1. User can play a complete round of the guessing game
2. Game provides correct high/low feedback
3. Round ends on correct guess or attempt exhaustion
4. Best score persists across browser sessions
5. App is deployed and accessible via GitHub Pages

These become the "Global Acceptance Criteria" section in AGENTS.md.
Each criterion must be verifiable — something a reviewer can check.
```

**Step 2: Commit**

```bash
git add .github/workflows/telegram-bot.md
git commit -m "prompt: Phase 3 remove MVP bias, add acceptance criteria"
```

---

### Task 3: Rewrite Phase 4 — Structured issue body (agentics format)

**Files:**
- Modify: `.github/workflows/telegram-bot.md` (Phase 4 section)

**Why:** Adopt agentics' issue body format (Objective/Context/Approach/Files/Acceptance Criteria) merged with our Validation section. Add dependency analysis for grouping.

**Step 1: Replace Phase 4 content**

Find:
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
   - Project goal and description
   - Tech stack with specific versions/choices
   - Architecture overview
   - References to open-source projects found in Phase 2
   - Global Acceptance Criteria (from Phase 3)
3. **Issue list** — plan backwards from acceptance criteria:
   a. List all features needed to meet the acceptance criteria
   b. Map dependencies: if A depends on B, mark them as coupled
   c. Merge tightly-coupled features into single issues
   d. Target 2-5 issues total, sequenced: foundation → implementation → polish/deploy
   e. Each issue body MUST follow this structure:

      ## Objective
      [What this issue delivers in user-visible terms]

      ## Context
      [Why this is needed, what depends on it]

      ## Approach
      1. [Step-by-step plan with specific actions]
      2. [Each step should be one commit]

      ## Files
      - Create: `exact/path/to/file.js`
      - Modify: `exact/path/to/existing.js`

      ## Acceptance Criteria
      - [ ] [Verifiable criterion 1]
      - [ ] [Verifiable criterion 2]

      ## Validation
      - [Exact steps to verify this works after completion]
      - [e.g. "Open index.html in browser, click Play, verify game starts"]

4. **Skills selection**: Pick from available templates:
   - Always include: `issue-workflow`, `code-standards`, `testing`
   - If deploying to Pages: include `deploy-pages`
```

**Step 2: Commit**

```bash
git add .github/workflows/telegram-bot.md
git commit -m "prompt: Phase 4 structured issue body with dependency analysis"
```

---

### Task 4: Update App Factory guidelines

**Files:**
- Modify: `.github/workflows/telegram-bot.md` (App Factory guidelines section)

**Step 1: Replace guidelines**

Find:
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
- Issues should be in English
- Target 2-5 issues based on dependency analysis (not 5-8)
- Merge tightly-coupled features into one issue
- Keep independent features as separate issues
- Each issue must represent a verifiable functional module
- Each issue body must include: Objective, Context, Approach, Files, Acceptance Criteria, Validation
- Each issue must be completable by Copilot CLI within the 55-minute timeout
- Sequence: foundation + core first → features → polish + deploy last
```

**Step 2: Commit**

```bash
git add .github/workflows/telegram-bot.md
git commit -m "prompt: guidelines for fewer, larger, structured issues"
```

---

### Task 5: Improve implement.yml — guided implementation (inspired by write-code skill)

**Files:**
- Modify: `.github/skills/app-factory/templates/workflows/implement.yml`

**Why:** Current prompt just says "Implement the feature." Apptopia's write-code skill has 7 phases including "verify before declaring done." We adopt the key principles: follow the approach steps, verify using acceptance criteria, commit per step.

**Step 1: Update the "Implement issue" Copilot prompt**

Find:
```yaml
          copilot --autopilot --yolo \
            --model gpt-5.3-codex \
            --max-autopilot-continues 30 \
            -p "
              You are an autonomous coding agent working on repository ${GH_REPO}.
              Read AGENTS.md to understand the project spec and tech stack.

              Implement issue #${ISSUE_NUM}.
              - Read the issue: gh issue view ${ISSUE_NUM}
              - You are already on branch issue-${ISSUE_NUM}-impl
              - Implement the feature following AGENTS.md
              - Write tests if applicable
              - git add, commit, push
              - Create PR: gh pr create --title 'Implement #${ISSUE_NUM}' --body 'Closes #${ISSUE_NUM}'
            "
```

Replace with:
```yaml
          copilot --autopilot --yolo \
            --model gpt-5.3-codex \
            --max-autopilot-continues 30 \
            -p "
              You are an autonomous coding agent working on repository ${GH_REPO}.
              Read AGENTS.md to understand the project spec, tech stack, and Global Acceptance Criteria.

              Implement issue #${ISSUE_NUM}:
              1. Read the issue: gh issue view ${ISSUE_NUM}
              2. The issue has these sections: Objective, Context, Approach, Files, Acceptance Criteria, Validation
              3. Follow the Approach steps in order — commit after each step
              4. Create/modify only the files listed in the Files section
              5. After all steps, verify using the Validation section
              6. Confirm each Acceptance Criteria checkbox is met
              7. You are already on branch issue-${ISSUE_NUM}-impl
              8. git add, commit, push
              9. Create PR: gh pr create --title 'Implement #${ISSUE_NUM}' --body 'Closes #${ISSUE_NUM}'

              If you cannot meet an acceptance criterion, explain why in the PR body.
            "
```

**Step 2: Update the "Fix PR" Copilot prompt**

Find:
```yaml
          copilot --autopilot --yolo \
            --model gpt-5.3-codex \
            --max-autopilot-continues 30 \
            -p "
              You are an autonomous coding agent working on repository ${GH_REPO}.
              Read AGENTS.md to understand the project spec and tech stack.

              PR #${PR_NUM} has changes requested by the reviewer.
              You are already on the PR branch.
              - Read review comments: gh pr view ${PR_NUM} --comments
              - Address ALL review comments with code changes
              - git add, commit, push
            "
```

Replace with:
```yaml
          copilot --autopilot --yolo \
            --model gpt-5.3-codex \
            --max-autopilot-continues 30 \
            -p "
              You are an autonomous coding agent working on repository ${GH_REPO}.
              Read AGENTS.md to understand the project spec and acceptance criteria.

              PR #${PR_NUM} has changes requested by the reviewer.
              You are already on the PR branch.
              1. Read review comments: gh pr view ${PR_NUM} --comments
              2. Read the linked issue for the Acceptance Criteria and Validation sections
              3. Address ALL review comments with code changes
              4. Re-verify using the Validation section
              5. git add, commit, push
            "
```

**Step 3: Commit**

```bash
git add .github/skills/app-factory/templates/workflows/implement.yml
git commit -m "template: guided implement prompt with approach steps and verification"
```

---

### Task 6: Improve review.yml — validation-aware review + fallback

**Files:**
- Modify: `.github/skills/app-factory/templates/workflows/review.yml`

**Why:** Current review prompt says "check code quality" without specifics. agentics' grumpy-reviewer MUST take an action (APPROVE or REQUEST_CHANGES). PR #9 showed our reviewer can exit without acting, stalling the chain.

**Step 1: Update the Review Copilot prompt**

Find:
```yaml
          copilot --autopilot --yolo \
            --model gpt-5.3-codex \
            --max-autopilot-continues 10 \
            -p "
              You are a code reviewer for repository ${GH_REPO}.
              Read AGENTS.md to understand the project spec and acceptance criteria.

              Review PR #${PR_NUM}.
              - Run: gh pr diff ${PR_NUM}
              - Read the linked issue for acceptance criteria
              - Check code quality, correctness, and completeness

              IF the code is good and meets all acceptance criteria:
                1. gh pr review ${PR_NUM} --approve -b 'LGTM - code meets requirements'
                2. gh pr merge ${PR_NUM} --squash --delete-branch

              IF there are issues:
                1. gh pr review ${PR_NUM} --request-changes -b '<specific feedback>'
            "
```

Replace with:
```yaml
          copilot --autopilot --yolo \
            --model gpt-5.3-codex \
            --max-autopilot-continues 10 \
            -p "
              You are a strict code reviewer for repository ${GH_REPO}.
              Read AGENTS.md to understand the project spec and Global Acceptance Criteria.

              Review PR #${PR_NUM}:
              1. Run: gh pr diff ${PR_NUM}
              2. Find the linked issue number from the PR body (Closes #N)
              3. Read the issue: gh issue view N
              4. Check each item in the Acceptance Criteria section
              5. Check each item in the Validation section
              6. Check code quality: no dead code, no hardcoded values, proper error handling

              You MUST take exactly one action before exiting:

              APPROVE (all criteria met, code is clean):
                gh pr review ${PR_NUM} --approve -b 'All acceptance criteria verified: [list checked items]'
                gh pr merge ${PR_NUM} --squash --delete-branch

              REQUEST CHANGES (any criterion not met):
                gh pr review ${PR_NUM} --request-changes -b 'Issues found: [list specific problems with file:line references]'

              IMPORTANT: You must run one of the above gh commands. Never exit without taking action.
            "
```

**Step 2: Add "Fallback if review took no action" step**

Insert this new step after `Review` and before `Notify merge`:

```yaml
      - name: Fallback if review took no action
        if: steps.count.outputs.review_count < 3 && success()
        env:
          GH_TOKEN: ${{ secrets.COPILOT_PAT }}
        run: |
          PR_NUM=${{ github.event.pull_request.number }}
          STATE=$(gh pr view ${PR_NUM} --json state --jq '.state')
          if [ "$STATE" = "OPEN" ]; then
            REVIEWS=$(gh api repos/${{ github.repository }}/pulls/${PR_NUM}/reviews \
              --jq '[.[] | select(.state == "APPROVED" or .state == "CHANGES_REQUESTED")] | length')
            if [ "$REVIEWS" -eq 0 ]; then
              echo "::warning::Review completed without action, auto-approving"
              gh pr review ${PR_NUM} --approve -b "Auto-approved: review completed without taking action"
              gh pr merge ${PR_NUM} --squash --delete-branch || true
            fi
          fi
```

**Step 3: Commit**

```bash
git add .github/skills/app-factory/templates/workflows/review.yml
git commit -m "template: validation-aware review + fallback for no-action reviews"
```

---

### Task 7: Compile and push

**Step 1: Compile**

```bash
gh aw compile
```

**Step 2: Commit compiled output**

```bash
git add .github/workflows/telegram-bot.lock.yml
git commit -m "chore: gh aw compile after v6 changes"
```

**Step 3: Push**

```bash
git push
```

**Step 4: Verify**

```bash
grep -c "MVP" .github/workflows/telegram-bot.md                    # Expected: 0
grep -c "5-8" .github/workflows/telegram-bot.md                    # Expected: 0
grep -c "2-5 issues" .github/workflows/telegram-bot.md             # Expected: 1
grep -c "Deep Research" .github/workflows/telegram-bot.md           # Expected: 1
grep -c "Plan backwards" .github/workflows/telegram-bot.md          # Expected: 1
grep -c "Acceptance Criteria" .github/workflows/telegram-bot.md     # Expected: >= 2
grep -c "Validation section" .github/skills/app-factory/templates/workflows/implement.yml  # Expected: 1
grep -c "MUST take exactly one" .github/skills/app-factory/templates/workflows/review.yml  # Expected: 1
grep -c "Fallback" .github/skills/app-factory/templates/workflows/review.yml               # Expected: 1
```
