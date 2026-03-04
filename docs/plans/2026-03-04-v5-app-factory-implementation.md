# App Factory Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `/app`, `/build`, and `/msg` Telegram commands that auto-create GitHub repos with AI agent workflows, enabling end-to-end autonomous app development.

**Architecture:** gh-aw Copilot agent evaluates feasibility and plans, safe-inputs execute GitHub operations (create repo, push files, create issues) via skill scripts. New repos use Copilot CLI for autonomous implement→review→merge loops. Notifications flow back to Telegram via aw-telegram-bot's notify.yml.

**Tech Stack:** gh-aw (Copilot engine), Python skill scripts, GitHub CLI (`gh`), Copilot CLI, GitHub Actions

---

## Task 1: Create notify.yml in aw-telegram-bot

This is the callback workflow that new repos use to send Telegram notifications. It must exist before anything else can use it.

**Files:**
- Create: `.github/workflows/notify.yml`

**Step 1: Create notify.yml**

```yaml
name: Send Telegram Notification

on:
  workflow_dispatch:
    inputs:
      chat_id:
        description: "Telegram chat ID"
        required: true
      text:
        description: "Notification text"
        required: true

jobs:
  notify:
    runs-on: ubuntu-latest
    timeout-minutes: 2
    steps:
      - name: Verify caller
        run: |
          if [[ "${{ github.actor }}" != "yazelin" && \
                "${{ github.actor }}" != "github-actions[bot]" ]]; then
            echo "::error::Unauthorized caller: ${{ github.actor }}"
            exit 1
          fi

      - name: Send Telegram message
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
        run: |
          curl -sf -X POST \
            "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -H "Content-Type: application/json" \
            -d "{\"chat_id\": \"${{ inputs.chat_id }}\", \"text\": $(echo '${{ inputs.text }}' | jq -Rs .)}"
```

**Step 2: Commit**

```bash
git add .github/workflows/notify.yml
git commit -m "feat: add notify.yml for Telegram callback notifications"
```

**Step 3: Push and verify**

```bash
git push origin main
```

Then verify via GitHub UI or:

```bash
gh workflow list --repo yazelin/aw-telegram-bot
```

Expected: `notify.yml` appears in the list.

**Step 4: Test manually**

```bash
gh workflow run notify.yml \
  --repo yazelin/aw-telegram-bot \
  -f chat_id="850654509" \
  -f text="Test notification from notify.yml"
```

Expected: You receive a Telegram message "Test notification from notify.yml".

**Step 5: Commit any fixes if needed**

---

## Task 2: Create new repo workflow templates

These are the fixed templates that get pushed to every new repo created by `/app`.

**Files:**
- Create: `.github/skills/app-factory/templates/workflows/implement.yml`
- Create: `.github/skills/app-factory/templates/workflows/review.yml`

**Step 1: Create implement.yml template**

```yaml
name: Implement Issue

on:
  workflow_dispatch:

concurrency:
  group: copilot-implement
  cancel-in-progress: false

jobs:
  implement:
    runs-on: ubuntu-latest
    timeout-minutes: 55
    steps:
      - name: Generate scoped token
        id: token
        uses: actions/create-github-app-token@v1
        with:
          app-id: ${{ secrets.APP_ID }}
          private-key: ${{ secrets.APP_PRIVATE_KEY }}
          repositories: ${{ github.event.repository.name }}

      - name: Checkout
        uses: actions/checkout@v5
        with:
          fetch-depth: 0
          token: ${{ steps.token.outputs.token }}

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "22"

      - name: Install Copilot CLI
        run: npm install -g @github/copilot

      - name: Configure git
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

      - name: Implement
        env:
          COPILOT_GITHUB_TOKEN: ${{ steps.token.outputs.token }}
          GH_TOKEN: ${{ steps.token.outputs.token }}
          GH_REPO: ${{ github.repository }}
          NOTIFY_REPO: PLACEHOLDER_NOTIFY_REPO
          NOTIFY_CHAT_ID: PLACEHOLDER_CHAT_ID
        run: |
          copilot --autopilot --yolo \
            --model gpt-5.3-codex \
            --max-autopilot-continues 30 \
            -p "
              You are an autonomous coding agent working on repository ${GH_REPO}.
              Read AGENTS.md to understand the project spec and tech stack.
              Read .github/skills/ to understand development standards.

              Check current state and act accordingly:

              CASE A: There is an open PR with review comments requesting changes.
                - Find the open PR: gh pr list --state open --json number,headRefName
                - Check out its branch: git checkout <branch>
                - Read review comments: gh pr view <number> --comments
                - Address ALL review comments with code changes
                - git add, commit, push to the same branch
                - The push will trigger review.yml automatically
                - Exit

              CASE B: No open PR, but there are open issues (excluding label:agent-stuck and label:needs-human-review).
                - Find the oldest open issue: gh issue list --state open --json number,title,labels --jq '[.[] | select(.labels | map(.name) | (contains([\"agent-stuck\"]) or contains([\"needs-human-review\"])) | not)] | sort_by(.number) | .[0]'
                - If no actionable issue found, go to CASE C
                - Create a branch: git checkout -b issue-<number>-<slug>
                - Implement the issue following AGENTS.md tech stack
                - Write tests if applicable
                - git add, commit, push
                - Create PR: gh pr create --title 'Implement #<number>: <title>' --body 'Closes #<number>\n\nSummary: ...\nValidation: ...'
                - Exit

              CASE C: No open PR, no actionable issues.
                - All work is complete
                - Notify: gh workflow run notify.yml --repo ${NOTIFY_REPO} -f chat_id=${NOTIFY_CHAT_ID} -f text='✅ ${GH_REPO} all issues completed!'
                - Exit

              ERROR HANDLING:
              If you cannot complete an issue after reasonable effort:
                - Comment on the issue explaining what went wrong
                - Add label: gh issue edit <number> --add-label agent-stuck
                - Notify: gh workflow run notify.yml --repo ${NOTIFY_REPO} -f chat_id=${NOTIFY_CHAT_ID} -f text='⚠️ ${GH_REPO} issue #<number> is stuck: <reason>'
                - Trigger self for next issue: gh workflow run implement.yml
                - Exit
            "
```

Save to `.github/skills/app-factory/templates/workflows/implement.yml`.

**Step 2: Create review.yml template**

```yaml
name: Code Review

on:
  pull_request:
    types: [opened, synchronize]

concurrency:
  group: copilot-review-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  review:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - name: Generate scoped token
        id: token
        uses: actions/create-github-app-token@v1
        with:
          app-id: ${{ secrets.APP_ID }}
          private-key: ${{ secrets.APP_PRIVATE_KEY }}
          repositories: ${{ github.event.repository.name }}

      - name: Checkout
        uses: actions/checkout@v5
        with:
          token: ${{ steps.token.outputs.token }}

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "22"

      - name: Install Copilot CLI
        run: npm install -g @github/copilot

      - name: Count previous reviews
        id: count
        env:
          GH_TOKEN: ${{ steps.token.outputs.token }}
        run: |
          PR_NUM=${{ github.event.pull_request.number }}
          COUNT=$(gh api repos/${{ github.repository }}/pulls/${PR_NUM}/reviews --jq 'length')
          echo "review_count=${COUNT}" >> "$GITHUB_OUTPUT"
          echo "Review count for PR #${PR_NUM}: ${COUNT}"

      - name: Bail if too many reviews
        if: ${{ steps.count.outputs.review_count >= 3 }}
        env:
          GH_TOKEN: ${{ steps.token.outputs.token }}
          NOTIFY_REPO: PLACEHOLDER_NOTIFY_REPO
          NOTIFY_CHAT_ID: PLACEHOLDER_CHAT_ID
        run: |
          PR_NUM=${{ github.event.pull_request.number }}
          ISSUE_NUM=$(gh pr view ${PR_NUM} --json body --jq '.body' | grep -oP 'Closes #\K\d+' || echo "")
          if [ -n "$ISSUE_NUM" ]; then
            gh issue edit ${ISSUE_NUM} --add-label needs-human-review
          fi
          gh workflow run notify.yml --repo ${NOTIFY_REPO} \
            -f chat_id="${NOTIFY_CHAT_ID}" \
            -f text="⚠️ ${{ github.repository }} PR #${PR_NUM} failed review 3 times, needs human review"
          gh workflow run implement.yml
          echo "Bailed: too many reviews"

      - name: Review
        if: ${{ steps.count.outputs.review_count < 3 }}
        env:
          COPILOT_GITHUB_TOKEN: ${{ steps.token.outputs.token }}
          GH_TOKEN: ${{ steps.token.outputs.token }}
          GH_REPO: ${{ github.repository }}
          NOTIFY_REPO: PLACEHOLDER_NOTIFY_REPO
          NOTIFY_CHAT_ID: PLACEHOLDER_CHAT_ID
        run: |
          PR_NUM=${{ github.event.pull_request.number }}

          copilot --autopilot \
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
                3. gh workflow run implement.yml (trigger next issue)
                4. gh workflow run notify.yml --repo ${NOTIFY_REPO} -f chat_id=${NOTIFY_CHAT_ID} -f text='🔀 ${GH_REPO} PR #${PR_NUM} merged'

              IF there are issues:
                1. gh pr review ${PR_NUM} --request-changes -b '<specific feedback>'
                2. gh workflow run implement.yml (to fix the PR)
            "
```

Save to `.github/skills/app-factory/templates/workflows/review.yml`.

**Step 3: Commit**

```bash
git add .github/skills/app-factory/templates/workflows/
git commit -m "feat: add implement.yml and review.yml workflow templates for new repos"
```

---

## Task 3: Create skill SKILL.md templates

Fixed Copilot Agent Skills that every new repo gets.

**Files:**
- Create: `.github/skills/app-factory/templates/skills/issue-workflow-SKILL.md`
- Create: `.github/skills/app-factory/templates/skills/code-standards-SKILL.md`
- Create: `.github/skills/app-factory/templates/skills/testing-SKILL.md`
- Create: `.github/skills/app-factory/templates/skills/deploy-pages-SKILL.md`

**Step 1: Create issue-workflow-SKILL.md**

```markdown
# Issue Workflow

## Picking Issues
- Always pick the oldest open issue (lowest number) that does NOT have `agent-stuck` or `needs-human-review` labels
- Read the full issue body and all comments before starting

## Branching
- Branch name: `issue-<number>-<short-slug>`
- Always branch from latest `main`
- One branch per issue, one PR per issue

## Pull Requests
- Title: `Implement #<number>: <short description>`
- Body must include:
  - `Closes #<number>` (for auto-close on merge)
  - Summary of what was implemented
  - How to validate (exact commands or steps)
- Request no reviewers (review.yml handles it automatically)

## Commit Messages
- Format: `feat: <description>` for new features
- Format: `fix: <description>` for bug fixes
- One logical commit per PR (squash on merge handles this)
```

**Step 2: Create code-standards-SKILL.md**

```markdown
# Code Standards

## General
- Write clean, readable code with meaningful variable names
- Keep functions small and focused (under 50 lines)
- No commented-out code
- No console.log/print statements left in production code

## Error Handling
- Always handle errors gracefully
- Provide user-friendly error messages
- Never silently swallow errors

## File Organization
- Group related files together
- Use clear, descriptive file names
- Keep the project structure flat unless complexity demands nesting
```

**Step 3: Create testing-SKILL.md**

```markdown
# Testing

## When to Test
- Write tests for core business logic
- Write tests for edge cases and error handling
- Skip tests for trivial UI-only code in MVP

## How to Test
- Use the testing framework appropriate for the tech stack
- Tests should be runnable with a single command
- Document the test command in README.md

## Validation
- Before creating a PR, verify the app works:
  - Open index.html in a browser (for web apps)
  - Run the CLI tool with sample input (for CLI tools)
  - Run the test suite if one exists
```

**Step 4: Create deploy-pages-SKILL.md**

```markdown
# Deploy to GitHub Pages

## Setup
- All static files must be in the repository root or a `docs/` folder
- Entry point is `index.html`
- No build step required for pure HTML/CSS/JS projects

## GitHub Pages Configuration
- Source: Deploy from branch `main`, folder `/ (root)` or `/docs`
- The repository must have Pages enabled in Settings

## Validation
- After merge to main, verify the site is live at:
  `https://<owner>.github.io/<repo-name>/`
```

**Step 5: Commit**

```bash
git add .github/skills/app-factory/templates/skills/
git commit -m "feat: add SKILL.md templates for new repos"
```

---

## Task 4: Create app-factory skill scripts

Python scripts that safe-inputs call to execute GitHub operations.

**Files:**
- Create: `.github/skills/app-factory/create_repo.py`
- Create: `.github/skills/app-factory/setup_repo.py`
- Create: `.github/skills/app-factory/create_issues.py`
- Create: `.github/skills/app-factory/setup_secrets.py`
- Create: `.github/skills/app-factory/trigger_workflow.py`
- Create: `.github/skills/app-factory/post_comment.py`
- Create: `.github/skills/app-factory/manage_labels.py`

**Step 1: Create create_repo.py**

```python
#!/usr/bin/env python3
"""
Create a GitHub repository.

Usage: python create_repo.py <owner/name> <description>
Output: JSON to stdout
  Success: {"ok": true, "repo": "owner/name", "url": "https://github.com/owner/name"}
  Failure: {"ok": false, "error": "..."}
"""
import json, subprocess, sys

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"ok": False, "error": "Usage: create_repo.py <owner/name> <description>"}))
        sys.exit(1)

    repo = sys.argv[1]
    description = sys.argv[2]
    owner, name = repo.split("/", 1)

    result = subprocess.run(
        ["gh", "repo", "create", repo,
         "--public", "--description", description,
         "--clone=false"],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print(json.dumps({"ok": False, "error": result.stderr.strip()[-500:]}))
        sys.exit(1)

    url = result.stdout.strip()
    print(json.dumps({"ok": True, "repo": repo, "url": url}))

if __name__ == "__main__":
    main()
```

**Step 2: Create setup_repo.py**

```python
#!/usr/bin/env python3
"""
Push initial files to a newly created repo.

Usage: python setup_repo.py <owner/name> <json_files>
  json_files: JSON string of [{"path": "relative/path", "content": "file content"}, ...]
Output: JSON to stdout
  Success: {"ok": true, "files_pushed": 5}
  Failure: {"ok": false, "error": "..."}
"""
import json, os, subprocess, sys, tempfile

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"ok": False, "error": "Usage: setup_repo.py <owner/name> <json_files>"}))
        sys.exit(1)

    repo = sys.argv[1]
    files = json.loads(sys.argv[2])

    with tempfile.TemporaryDirectory() as tmpdir:
        # Clone the empty repo
        result = subprocess.run(
            ["gh", "repo", "clone", repo, tmpdir, "--", "--depth=1"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(json.dumps({"ok": False, "error": f"Clone failed: {result.stderr.strip()[-300:]}"}))
            sys.exit(1)

        # Write files
        for f in files:
            filepath = os.path.join(tmpdir, f["path"])
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as fh:
                fh.write(f["content"])

        # Git add, commit, push
        env = {**os.environ, "GIT_DIR": os.path.join(tmpdir, ".git"), "GIT_WORK_TREE": tmpdir}
        subprocess.run(["git", "config", "user.name", "github-actions[bot]"],
                       cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "config", "user.email",
                       "41898282+github-actions[bot]@users.noreply.github.com"],
                       cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "add", "-A"], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit: project setup"],
                       cwd=tmpdir, capture_output=True)
        result = subprocess.run(["git", "push", "origin", "main"],
                               cwd=tmpdir, capture_output=True, text=True)
        if result.returncode != 0:
            print(json.dumps({"ok": False, "error": f"Push failed: {result.stderr.strip()[-300:]}"}))
            sys.exit(1)

    print(json.dumps({"ok": True, "files_pushed": len(files)}))

if __name__ == "__main__":
    main()
```

**Step 3: Create create_issues.py**

```python
#!/usr/bin/env python3
"""
Create multiple issues in a repo.

Usage: python create_issues.py <owner/name> <json_issues>
  json_issues: JSON string of [{"title": "...", "body": "..."}, ...]
Output: JSON to stdout
  Success: {"ok": true, "issues_created": 5, "numbers": [1,2,3,4,5]}
  Failure: {"ok": false, "error": "..."}
"""
import json, subprocess, sys

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"ok": False, "error": "Usage: create_issues.py <owner/name> <json_issues>"}))
        sys.exit(1)

    repo = sys.argv[1]
    issues = json.loads(sys.argv[2])
    numbers = []

    for issue in issues:
        result = subprocess.run(
            ["gh", "issue", "create",
             "--repo", repo,
             "--title", issue["title"],
             "--body", issue["body"]],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(json.dumps({"ok": False, "error": f"Failed to create '{issue['title']}': {result.stderr.strip()[-300:]}"}))
            sys.exit(1)
        # gh issue create outputs the URL, extract number
        url = result.stdout.strip()
        number = int(url.rstrip("/").split("/")[-1])
        numbers.append(number)

    print(json.dumps({"ok": True, "issues_created": len(numbers), "numbers": numbers}))

if __name__ == "__main__":
    main()
```

**Step 4: Create setup_secrets.py**

```python
#!/usr/bin/env python3
"""
Set secrets on a repo.

Usage: python setup_secrets.py <owner/name> <json_secrets>
  json_secrets: JSON string of [{"name": "SECRET_NAME", "value": "secret_value"}, ...]
Output: JSON to stdout
  Success: {"ok": true, "secrets_set": 1}
  Failure: {"ok": false, "error": "..."}
"""
import json, subprocess, sys

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"ok": False, "error": "Usage: setup_secrets.py <owner/name> <json_secrets>"}))
        sys.exit(1)

    repo = sys.argv[1]
    secrets = json.loads(sys.argv[2])

    for s in secrets:
        result = subprocess.run(
            ["gh", "secret", "set", s["name"],
             "--repo", repo,
             "--body", s["value"]],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(json.dumps({"ok": False, "error": f"Failed to set {s['name']}: {result.stderr.strip()[-300:]}"}))
            sys.exit(1)

    print(json.dumps({"ok": True, "secrets_set": len(secrets)}))

if __name__ == "__main__":
    main()
```

**Step 5: Create trigger_workflow.py**

```python
#!/usr/bin/env python3
"""
Trigger a workflow in a repo.

Usage: python trigger_workflow.py <owner/name> <workflow_file>
Output: JSON to stdout
  Success: {"ok": true, "repo": "owner/name", "workflow": "implement.yml"}
  Failure: {"ok": false, "error": "..."}
"""
import json, subprocess, sys

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"ok": False, "error": "Usage: trigger_workflow.py <owner/name> <workflow_file>"}))
        sys.exit(1)

    repo = sys.argv[1]
    workflow = sys.argv[2]

    result = subprocess.run(
        ["gh", "workflow", "run", workflow, "--repo", repo],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print(json.dumps({"ok": False, "error": result.stderr.strip()[-500:]}))
        sys.exit(1)

    print(json.dumps({"ok": True, "repo": repo, "workflow": workflow}))

if __name__ == "__main__":
    main()
```

**Step 6: Create post_comment.py**

```python
#!/usr/bin/env python3
"""
Post a comment on an issue or PR.

Usage: python post_comment.py <owner/name> <number> <body>
Output: JSON to stdout
  Success: {"ok": true, "repo": "owner/name", "number": 3, "type": "issue"}
  Failure: {"ok": false, "error": "..."}
"""
import json, subprocess, sys

def main():
    if len(sys.argv) < 4:
        print(json.dumps({"ok": False, "error": "Usage: post_comment.py <owner/name> <number> <body>"}))
        sys.exit(1)

    repo = sys.argv[1]
    number = sys.argv[2]
    body = sys.argv[3]

    # Determine if it's an issue or PR
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/pulls/{number}"],
        capture_output=True, text=True
    )
    is_pr = result.returncode == 0

    if is_pr:
        cmd = ["gh", "pr", "comment", number, "--repo", repo, "--body", body]
        item_type = "pr"
    else:
        cmd = ["gh", "issue", "comment", number, "--repo", repo, "--body", body]
        item_type = "issue"

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(json.dumps({"ok": False, "error": result.stderr.strip()[-300:]}))
        sys.exit(1)

    print(json.dumps({"ok": True, "repo": repo, "number": int(number), "type": item_type}))

if __name__ == "__main__":
    main()
```

**Step 7: Create manage_labels.py**

```python
#!/usr/bin/env python3
"""
Add or remove labels on an issue or PR.

Usage: python manage_labels.py <owner/name> <number> <action> <label>
  action: "add" or "remove"
Output: JSON to stdout
  Success: {"ok": true, "action": "remove", "label": "agent-stuck"}
  Failure: {"ok": false, "error": "..."}
"""
import json, subprocess, sys

def main():
    if len(sys.argv) < 5:
        print(json.dumps({"ok": False, "error": "Usage: manage_labels.py <owner/name> <number> <add|remove> <label>"}))
        sys.exit(1)

    repo = sys.argv[1]
    number = sys.argv[2]
    action = sys.argv[3]
    label = sys.argv[4]

    if action == "add":
        cmd = ["gh", "issue", "edit", number, "--repo", repo, "--add-label", label]
    elif action == "remove":
        cmd = ["gh", "issue", "edit", number, "--repo", repo, "--remove-label", label]
    else:
        print(json.dumps({"ok": False, "error": f"Unknown action: {action}. Use 'add' or 'remove'."}))
        sys.exit(1)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(json.dumps({"ok": False, "error": result.stderr.strip()[-300:]}))
        sys.exit(1)

    print(json.dumps({"ok": True, "action": action, "label": label}))

if __name__ == "__main__":
    main()
```

**Step 8: Commit**

```bash
git add .github/skills/app-factory/*.py
git commit -m "feat: add app-factory skill scripts (create-repo, setup, issues, secrets, trigger, comment, labels)"
```

---

## Task 5: Add safe-inputs for app-factory operations

Add new safe-inputs to `telegram-bot.md` that wrap the skill scripts.

**Files:**
- Modify: `.github/workflows/telegram-bot.md` (safe-inputs section, after `send-telegram-video`)

**Step 1: Add new secrets to secrets section**

In `telegram-bot.md`, find the `secrets:` block (line ~207) and add:

```yaml
secrets:
  TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
  TAVILY_API_KEY: ${{ secrets.TAVILY_API_KEY }}
  FACTORY_PAT: ${{ secrets.FACTORY_PAT }}
  APP_ID: ${{ secrets.APP_ID }}
  APP_PRIVATE_KEY: ${{ secrets.APP_PRIVATE_KEY }}
```

**Step 2: Add safe-inputs after send-telegram-video (before `secrets:` block)**

Add the following safe-inputs after the `send-telegram-video` block (after line ~205):

```yaml
  create-repo:
    description: "Create a new GitHub repository"
    inputs:
      owner:
        type: string
        required: true
        description: "Repository owner (e.g. yazelin)"
      name:
        type: string
        required: true
        description: "Repository name (e.g. minesweeper-web)"
      repo_description:
        type: string
        required: true
        description: "Short description for the repository"
    py: |
      import subprocess, sys, os, json
      owner = inputs.get("owner", "")
      name = inputs.get("name", "")
      desc = inputs.get("repo_description", "")
      repo = f"{owner}/{name}"
      workspace = os.environ.get("GITHUB_WORKSPACE", "")
      script = os.path.join(workspace, ".github", "skills", "app-factory", "create_repo.py")
      result = subprocess.run(
          [sys.executable, script, repo, desc],
          capture_output=True, text=True, timeout=60,
          env={**os.environ}
      )
      if result.returncode != 0:
          print(json.dumps({"ok": False, "error": result.stderr.strip()[-300:] or "Failed"}))
      else:
          print(result.stdout)
    env:
      GH_TOKEN: "${{ secrets.FACTORY_PAT }}"
    timeout: 60

  setup-repo:
    description: "Push initial files to a repository"
    inputs:
      repo:
        type: string
        required: true
        description: "Repository full name (e.g. yazelin/minesweeper-web)"
      files_json:
        type: string
        required: true
        description: "JSON array of {path, content} objects to push"
    py: |
      import subprocess, sys, os, json
      repo = inputs.get("repo", "")
      files_json = inputs.get("files_json", "[]")
      workspace = os.environ.get("GITHUB_WORKSPACE", "")
      script = os.path.join(workspace, ".github", "skills", "app-factory", "setup_repo.py")
      result = subprocess.run(
          [sys.executable, script, repo, files_json],
          capture_output=True, text=True, timeout=120,
          env={**os.environ}
      )
      if result.returncode != 0:
          print(json.dumps({"ok": False, "error": result.stderr.strip()[-300:] or "Failed"}))
      else:
          print(result.stdout)
    env:
      GH_TOKEN: "${{ secrets.FACTORY_PAT }}"
    timeout: 120

  create-issues:
    description: "Create multiple issues in a repository"
    inputs:
      repo:
        type: string
        required: true
        description: "Repository full name (e.g. yazelin/minesweeper-web)"
      issues_json:
        type: string
        required: true
        description: "JSON array of {title, body} objects"
    py: |
      import subprocess, sys, os, json
      repo = inputs.get("repo", "")
      issues_json = inputs.get("issues_json", "[]")
      workspace = os.environ.get("GITHUB_WORKSPACE", "")
      script = os.path.join(workspace, ".github", "skills", "app-factory", "create_issues.py")
      result = subprocess.run(
          [sys.executable, script, repo, issues_json],
          capture_output=True, text=True, timeout=120,
          env={**os.environ}
      )
      if result.returncode != 0:
          print(json.dumps({"ok": False, "error": result.stderr.strip()[-300:] or "Failed"}))
      else:
          print(result.stdout)
    env:
      GH_TOKEN: "${{ secrets.FACTORY_PAT }}"
    timeout: 120

  setup-secrets:
    description: "Set secrets on a repository"
    inputs:
      repo:
        type: string
        required: true
        description: "Repository full name"
      secrets_json:
        type: string
        required: true
        description: "JSON array of {name, value} objects"
    py: |
      import subprocess, sys, os, json
      repo = inputs.get("repo", "")
      secrets_json = inputs.get("secrets_json", "[]")
      workspace = os.environ.get("GITHUB_WORKSPACE", "")
      script = os.path.join(workspace, ".github", "skills", "app-factory", "setup_secrets.py")
      result = subprocess.run(
          [sys.executable, script, repo, secrets_json],
          capture_output=True, text=True, timeout=60,
          env={**os.environ}
      )
      if result.returncode != 0:
          print(json.dumps({"ok": False, "error": result.stderr.strip()[-300:] or "Failed"}))
      else:
          print(result.stdout)
    env:
      GH_TOKEN: "${{ secrets.FACTORY_PAT }}"
      APP_ID_VALUE: "${{ secrets.APP_ID }}"
      APP_PRIVATE_KEY_VALUE: "${{ secrets.APP_PRIVATE_KEY }}"
    timeout: 60

  trigger-workflow:
    description: "Trigger a workflow in a repository"
    inputs:
      repo:
        type: string
        required: true
        description: "Repository full name"
      workflow:
        type: string
        required: true
        description: "Workflow filename (e.g. implement.yml)"
    py: |
      import subprocess, sys, os, json
      repo = inputs.get("repo", "")
      workflow = inputs.get("workflow", "")
      workspace = os.environ.get("GITHUB_WORKSPACE", "")
      script = os.path.join(workspace, ".github", "skills", "app-factory", "trigger_workflow.py")
      result = subprocess.run(
          [sys.executable, script, repo, workflow],
          capture_output=True, text=True, timeout=30,
          env={**os.environ}
      )
      if result.returncode != 0:
          print(json.dumps({"ok": False, "error": result.stderr.strip()[-300:] or "Failed"}))
      else:
          print(result.stdout)
    env:
      GH_TOKEN: "${{ secrets.FACTORY_PAT }}"
    timeout: 30

  post-comment:
    description: "Post a comment on an issue or PR in any repo"
    inputs:
      repo:
        type: string
        required: true
        description: "Repository full name"
      number:
        type: string
        required: true
        description: "Issue or PR number"
      body:
        type: string
        required: true
        description: "Comment body text"
    py: |
      import subprocess, sys, os, json
      repo = inputs.get("repo", "")
      number = inputs.get("number", "")
      body = inputs.get("body", "")
      workspace = os.environ.get("GITHUB_WORKSPACE", "")
      script = os.path.join(workspace, ".github", "skills", "app-factory", "post_comment.py")
      result = subprocess.run(
          [sys.executable, script, repo, number, body],
          capture_output=True, text=True, timeout=30,
          env={**os.environ}
      )
      if result.returncode != 0:
          print(json.dumps({"ok": False, "error": result.stderr.strip()[-300:] or "Failed"}))
      else:
          print(result.stdout)
    env:
      GH_TOKEN: "${{ secrets.FACTORY_PAT }}"
    timeout: 30

  manage-labels:
    description: "Add or remove a label on an issue or PR"
    inputs:
      repo:
        type: string
        required: true
        description: "Repository full name"
      number:
        type: string
        required: true
        description: "Issue or PR number"
      action:
        type: string
        required: true
        description: "'add' or 'remove'"
      label:
        type: string
        required: true
        description: "Label name"
    py: |
      import subprocess, sys, os, json
      repo = inputs.get("repo", "")
      number = inputs.get("number", "")
      action = inputs.get("action", "")
      label = inputs.get("label", "")
      workspace = os.environ.get("GITHUB_WORKSPACE", "")
      script = os.path.join(workspace, ".github", "skills", "app-factory", "manage_labels.py")
      result = subprocess.run(
          [sys.executable, script, repo, number, action, label],
          capture_output=True, text=True, timeout=30,
          env={**os.environ}
      )
      if result.returncode != 0:
          print(json.dumps({"ok": False, "error": result.stderr.strip()[-300:] or "Failed"}))
      else:
          print(result.stdout)
    env:
      GH_TOKEN: "${{ secrets.FACTORY_PAT }}"
    timeout: 30
```

**Step 3: Commit**

```bash
git add .github/workflows/telegram-bot.md
git commit -m "feat: add app-factory safe-inputs (create-repo, setup-repo, create-issues, setup-secrets, trigger-workflow, post-comment, manage-labels)"
```

---

## Task 6: Update prompt with /app, /build, /msg commands

Add the three new command routes and their workflows to the prompt section of `telegram-bot.md`.

**Files:**
- Modify: `.github/workflows/telegram-bot.md` (prompt section, after the YAML frontmatter `---`)

**Step 1: Update the chatbot description and instructions**

Replace the opening lines after `---` (starting at line ~215):

```markdown
# Telegram Chatbot

You are a helpful, friendly AI assistant responding to a Telegram message.
You can generate images, research topics, translate text, download videos,
create app projects, trigger builds, and send messages to repos.
```

Update the instructions command list:

```markdown
## Instructions

1. Check the message for a command prefix:
   - `/app <description>` → App Factory mode
   - `/build <owner/repo>` → Build trigger mode
   - `/msg <owner/repo>#<number> <message>` → Message relay mode
   - `/research <topic>` → Research mode
   - `/draw <description>` → Image generation mode
   - `/translate <text>` → Translation mode
   - `/download <url>` → Video download mode
   - No prefix → Auto-judge: pick the best mode based on content
2. Execute the appropriate workflow below.
3. Always send exactly one response — a photo, a video, or a text message.
```

**Step 2: Add App Factory workflow section** (after Video download workflow)

```markdown
## App Factory workflow

Use this when the user sends `/app <description>` to create a new app project.

### Phase 1: Evaluate feasibility

1. Analyze the user's description to understand what they want
2. Evaluate if it's feasible as an MVP:
   - Is the scope reasonable for automated development?
   - Are there legal/security/privacy concerns?
   - Is it technically achievable with standard web technologies?
3. If NOT feasible, send a detailed explanation via `send-telegram-message` and stop

### Phase 2: Search for existing solutions

1. Use `web-search` to find relevant open-source projects or libraries
2. Decide: build from scratch, reference an existing project, or suggest a fork

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

### Phase 5: Execute

Call safe-inputs in this order:

1. `create-repo` with owner=`yazelin`, name=`<repo-name>`, description
2. `setup-repo` with all files:
   - `README.md` (dynamic)
   - `AGENTS.md` (dynamic)
   - `.github/workflows/implement.yml` (from template, with PLACEHOLDER_NOTIFY_REPO replaced with `yazelin/aw-telegram-bot` and PLACEHOLDER_CHAT_ID replaced with the chat_id from this message)
   - `.github/workflows/review.yml` (from template, same placeholder replacements)
   - `.github/skills/issue-workflow/SKILL.md` (from template)
   - `.github/skills/code-standards/SKILL.md` (from template)
   - `.github/skills/testing/SKILL.md` (from template)
   - `.github/skills/deploy-pages/SKILL.md` (if applicable)
3. `create-issues` with the planned issues
4. `setup-secrets` with `[{"name": "APP_ID", "value": "<from env>"}, {"name": "APP_PRIVATE_KEY", "value": "<from env>"}]`
   - APP_ID is available in the APP_ID_VALUE environment variable
   - APP_PRIVATE_KEY is available in the APP_PRIVATE_KEY_VALUE environment variable
5. `send-telegram-message` with:
   - Summary: repo URL, number of issues created, tech stack chosen
   - Instructions: "Send `/build yazelin/<repo-name>` to start development"

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

## Build trigger workflow

Use this when the user sends `/build <owner/repo>`.

1. Parse the repo name from the message
2. Verify the repo exists by checking if `trigger-workflow` can reach it
3. Call `trigger-workflow` with repo and workflow=`implement.yml`
4. Send confirmation via `send-telegram-message`:
   "🚀 已觸發 <repo> 開發流程，可到 https://github.com/<repo>/actions 查看進度"

### Build trigger guidelines

- The repo must already exist (created by `/app`)
- If the repo doesn't exist, explain that they need to run `/app` first

## Message relay workflow

Use this when the user sends `/msg <owner/repo>#<number> <message>`.

1. Parse the command:
   - Extract repo (e.g. `yazelin/minesweeper-web`)
   - Extract number (e.g. `3`)
   - Extract message (everything after the number)
2. Call `post-comment` with:
   - repo, number
   - body: "📝 User instruction:\n\n<message>"
3. Check if the issue/PR has `agent-stuck` or `needs-human-review` label:
   - If yes: call `manage-labels` to remove the label
   - Then call `trigger-workflow` to restart implement.yml
4. Send confirmation via `send-telegram-message`:
   "📝 已將指示傳達給 <repo> #<number>"

### Message relay guidelines

- The `/msg` format is: `/msg owner/repo#number message text here`
- If parsing fails, explain the correct format
- Always prefix the comment with "📝 User instruction:" so Copilot CLI knows it's a human directive
```

**Step 3: Commit**

```bash
git add .github/workflows/telegram-bot.md
git commit -m "feat: add /app, /build, /msg command routing and workflows to prompt"
```

---

## Task 7: Create tokens and push

Before testing, you need a Classic PAT for aw-telegram-bot and a GitHub App for new repos.

**Step 1: Create FACTORY_PAT (Classic PAT)**

Go to https://github.com/settings/tokens and create a Classic PAT with:
- Scopes: `repo`, `workflow`
- Expiration: 90 days (or as preferred)
- Name: `FACTORY_PAT for aw-telegram-bot`

```bash
gh secret set FACTORY_PAT --repo yazelin/aw-telegram-bot
# Paste the PAT when prompted
```

**Step 2: Create GitHub App**

Go to https://github.com/settings/apps/new and create a GitHub App:
- Name: `aw-app-factory` (or similar)
- Homepage URL: `https://github.com/yazelin/aw-telegram-bot`
- Uncheck Webhook (Active)
- Permissions:
  - Repository: Contents (Read & Write), Issues (Read & Write), Pull requests (Read & Write), Workflows (Read & Write)
- Where can this app be installed: Only on this account
- Click "Create GitHub App"

Note the **App ID** shown on the app settings page.

**Step 3: Generate private key**

On the app settings page, scroll to "Private keys" and click "Generate a private key".
A `.pem` file will be downloaded.

**Step 4: Install the app on your account**

Go to the app's page → "Install App" → Install on your account → select "All repositories" (so it works on future repos too).

**Step 5: Add secrets to aw-telegram-bot**

```bash
gh secret set APP_ID --repo yazelin/aw-telegram-bot
# Enter the App ID number

gh secret set APP_PRIVATE_KEY --repo yazelin/aw-telegram-bot < path/to/your-app.pem
```

**Step 6: Push all changes**

```bash
git push origin main
```

**Step 7: Verify workflow compiles**

Check that the gh-aw workflow compiles without errors by viewing the Actions tab on GitHub.

---

## Task 8: End-to-end test with /app

**Step 1: Send test message**

Send to Telegram bot:

```
/app 建立一個簡單的猜數字遊戲網頁
```

**Step 2: Verify the flow**

Expected:
1. Bot evaluates feasibility → feasible
2. Bot creates repo `yazelin/guess-number-game` (or similar)
3. Bot pushes README.md, AGENTS.md, workflows, skills
4. Bot creates 3-5 issues
5. Bot sets APP_ID + APP_PRIVATE_KEY secrets on new repo
6. Bot replies with repo URL and issue count

**Step 3: Verify new repo structure**

```bash
gh repo view yazelin/<repo-name> --json name,description
gh issue list --repo yazelin/<repo-name>
```

Expected: Repo exists with README, AGENTS.md, workflows, skills, and issues.

**Step 4: Test /build**

Send to Telegram bot:

```
/build yazelin/<repo-name>
```

Expected: Bot triggers implement.yml, you receive confirmation.

**Step 5: Watch the automation loop**

Monitor on GitHub Actions:
1. implement.yml picks first issue → creates PR
2. review.yml triggers → reviews → merges (or requests changes)
3. implement.yml triggers again → picks next issue
4. Repeat until done
5. You receive Telegram notification for each merge and when all done

**Step 6: Test /msg (if anything gets stuck)**

If an issue gets stuck:

```
/msg yazelin/<repo-name>#<issue-number> <your instructions>
```

Expected: Comment posted, label removed, implement.yml re-triggered.

---

## Task Summary

| Task | What | Files |
|------|------|-------|
| 1 | notify.yml callback workflow | `.github/workflows/notify.yml` |
| 2 | Workflow templates for new repos | `.github/skills/app-factory/templates/workflows/` |
| 3 | SKILL.md templates for new repos | `.github/skills/app-factory/templates/skills/` |
| 4 | Python skill scripts | `.github/skills/app-factory/*.py` |
| 5 | Safe-inputs in telegram-bot.md | `.github/workflows/telegram-bot.md` |
| 6 | Prompt update (/app, /build, /msg) | `.github/workflows/telegram-bot.md` |
| 7 | Create PAT + push | GitHub settings + `gh secret set` |
| 8 | End-to-end testing | Manual verification |

Tasks 1-6 are code changes. Task 7 requires manual GitHub setup. Task 8 is testing.
