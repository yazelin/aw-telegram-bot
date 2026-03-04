# Smart Issue Planning Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Optimize App Factory to create fewer, larger, verifiable issues (2-5 instead of 5-8), improve implement/review prompts, add review fallback, and enhance AGENTS.md template.

**Architecture:** Changes span 3 areas:
1. Parent repo prompt (`telegram-bot.md`) — smarter issue planning
2. Child repo templates (`implement.yml`, `review.yml`) — better prompts + review fallback
3. No Python script changes — same JSON interfaces

**Tech Stack:** gh-aw prompt markdown, GitHub Actions YAML

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

### Task 2: Expand Phase 3 — Define "Done"

**Files:**
- Modify: `.github/workflows/telegram-bot.md` (Phase 3 section)

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
1. User can play a complete round of the guessing game
2. Game provides correct high/low feedback
3. Round ends on correct guess or attempt exhaustion
4. Best score persists across browser sessions
5. App is deployed and accessible via GitHub Pages

These become the "Global Acceptance Criteria" section in AGENTS.md.
```

**Step 2: Commit**

```bash
git add .github/workflows/telegram-bot.md
git commit -m "prompt: Phase 3 add whole-app acceptance criteria"
```

---

### Task 3: Rewrite Phase 4 — Plan Backwards

**Files:**
- Modify: `.github/workflows/telegram-bot.md` (Phase 4 section)

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
   e. Each issue body MUST follow this structure:
      ```
      ## Objective
      [What this issue delivers in user-visible terms]

      ## Steps
      - [ ] Step 1: ...
      - [ ] Step 2: ...

      ## Files
      - Create: `file1.js`, `file2.css`
      - Modify: `README.md`

      ## Validation
      - [How to verify this works after completion]
      ```
4. **Skills selection**: Pick from available templates:
   - Always include: `issue-workflow`, `code-standards`, `testing`
   - If deploying to Pages: include `deploy-pages`
```

**Step 2: Commit**

```bash
git add .github/workflows/telegram-bot.md
git commit -m "prompt: Phase 4 dependency-aware issue planning with structured body"
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
- Issues should be in English with clear acceptance criteria
- Target 2-5 issues based on dependency analysis
- Merge tightly-coupled features into one issue
- Keep independent features as separate issues
- Each issue should represent a verifiable functional module
- Include a step-by-step checklist and Validation section in each issue
- Each issue should be completable by Copilot CLI within the 55-minute timeout
- First issue should include the project skeleton + core functionality
- Last issue should handle deployment and final polish (if applicable)
```

**Step 2: Commit**

```bash
git add .github/workflows/telegram-bot.md
git commit -m "prompt: update guidelines for fewer, larger issues"
```

---

### Task 5: Improve implement.yml template — guided implementation

**Files:**
- Modify: `.github/skills/app-factory/templates/workflows/implement.yml`

**Step 1: Update the "Implement issue" Copilot prompt**

Find the implement prompt (in the `Implement issue` step):
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
              Read AGENTS.md to understand the project spec, tech stack, and acceptance criteria.

              Implement issue #${ISSUE_NUM}.
              - Read the issue: gh issue view ${ISSUE_NUM}
              - The issue contains Objective, Steps, Files, and Validation sections
              - Follow the Steps checklist in order, committing after each step
              - You are already on branch issue-${ISSUE_NUM}-impl
              - After completing all steps, verify using the Validation section
              - git add, commit, push
              - Create PR: gh pr create --title 'Implement #${ISSUE_NUM}' --body 'Closes #${ISSUE_NUM}'
            "
```

**Step 2: Commit**

```bash
git add .github/skills/app-factory/templates/workflows/implement.yml
git commit -m "template: improve implement prompt with step-by-step guidance"
```

---

### Task 6: Improve review.yml template — validation-aware review + fallback

**Files:**
- Modify: `.github/skills/app-factory/templates/workflows/review.yml`

**Step 1: Update the Review Copilot prompt**

Find the review prompt (in the `Review` step):
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
              You are a code reviewer for repository ${GH_REPO}.
              Read AGENTS.md to understand the project spec and acceptance criteria.

              Review PR #${PR_NUM}.
              1. Run: gh pr diff ${PR_NUM}
              2. Read the linked issue — find the Validation section
              3. Check each validation criterion against the code
              4. Check code quality, correctness, and completeness

              You MUST take exactly one of these actions:

              IF the code meets all validation criteria and is correct:
                1. gh pr review ${PR_NUM} --approve -b 'LGTM - all validation criteria met'
                2. gh pr merge ${PR_NUM} --squash --delete-branch

              IF there are issues:
                1. gh pr review ${PR_NUM} --request-changes -b '<list specific issues>'

              IMPORTANT: You must either approve+merge or request changes. Never exit without taking action.
            "
```

**Step 2: Add a "Fallback merge" step after Review**

Add this new step after the `Review` step and before the `Notify merge` step:

```yaml
      - name: Fallback if review took no action
        if: steps.count.outputs.review_count < 3 && success()
        env:
          GH_TOKEN: ${{ secrets.COPILOT_PAT }}
        run: |
          PR_NUM=${{ github.event.pull_request.number }}
          STATE=$(gh pr view ${PR_NUM} --json state --jq '.state')
          if [ "$STATE" = "OPEN" ]; then
            # Review ran but didn't approve or request changes — auto-approve and merge
            REVIEWS=$(gh api repos/${{ github.repository }}/pulls/${PR_NUM}/reviews --jq '[.[] | select(.state == "APPROVED" or .state == "CHANGES_REQUESTED")] | length')
            if [ "$REVIEWS" -eq 0 ]; then
              echo "::warning::Review took no action, auto-approving"
              gh pr review ${PR_NUM} --approve -b "Auto-approved: review completed without action"
              gh pr merge ${PR_NUM} --squash --delete-branch || true
            fi
          fi
```

**Step 3: Commit**

```bash
git add .github/skills/app-factory/templates/workflows/review.yml
git commit -m "template: validation-aware review prompt + fallback for no-action reviews"
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
git commit -m "chore: gh aw compile after v6 prompt and template changes"
```

**Step 3: Push all commits**

```bash
git push
```

**Step 4: Verify**

```bash
grep -c "5-8" .github/workflows/telegram-bot.md              # Expected: 0
grep -c "2-5 issues" .github/workflows/telegram-bot.md       # Expected: 1
grep -c "Deep Research" .github/workflows/telegram-bot.md     # Expected: 1
grep -c "Plan backwards" .github/workflows/telegram-bot.md   # Expected: 1
grep -c "Validation section" .github/skills/app-factory/templates/workflows/implement.yml  # Expected: 1
grep -c "Fallback" .github/skills/app-factory/templates/workflows/review.yml               # Expected: 1
```
