# Smart Issue Planning Design

## Problem

Current App Factory creates 5-8 small issues per project. In practice, most issues result in 1-30 lines of code changes, wasting 2 premium requests each (implement + review). Example: 6 issues for a number guessing game, 4 of which changed fewer than 10 lines.

## Design Philosophy

**Begin with the end in mind.** Diverge to research, then converge to verifiable outcomes.

```
User input → Diverge (research) → Define "done" → Converge (plan backwards)
```

Each issue must pass this test: **"Can we verify this works after completion?"**

## Architecture

Only the parent repo's prompt (telegram-bot.md Phase 2-4) changes. No changes to:
- `create_issues.py` (same JSON interface)
- `setup_repo.py`, `setup_secrets.py`
- Child repo's `implement.yml`, `review.yml`
- Event-driven workflow chain

## Changes

### Phase 2: Deep Research (Diverge)

**Before**: Quick web search to see if similar projects exist.

**After**:
1. `web-search` for 2-3 similar open-source projects
2. `web-fetch` to read their README and file structure
3. Extract: typical modules, file organization, feature breakdown
4. Note what features are tightly coupled vs independent

### Phase 3: Define the End State (Define "done")

**Before**: Only tech stack decisions.

**After**: Tech stack decisions + **whole-app acceptance criteria**.

Write a clear definition of "done" for the entire app:
```
## App Acceptance Criteria
1. User can play a complete round of the guessing game
2. Game provides correct high/low feedback
3. Round ends on correct guess or attempt exhaustion
4. Best score persists across browser sessions
5. App is deployed and accessible via GitHub Pages
```

This becomes the top section of AGENTS.md's "Global Acceptance Criteria".

### Phase 4: Plan Backwards (Converge)

**Before**: "Create 5-8 smaller issues, each independently implementable."

**After**:

1. **List all features** needed to meet the acceptance criteria
2. **Map dependencies**:
   - A depends on B → mark as coupled
   - A is independent of B → can be separate issues
3. **Merge coupled features** into single issues
4. **Target 2-5 issues** total, each representing a meaningful functional module
5. **Each issue includes**:
   - Step-by-step checklist (Copilot commits per step)
   - Files to create/modify
   - Validation section (how to verify it works)

### Issue Body Structure

```markdown
## Objective
[What this issue delivers in user-visible terms]

## Steps
- [ ] Step 1: Create project skeleton (index.html, style.css, script.js)
- [ ] Step 2: Implement random number generation and comparison logic
- [ ] Step 3: Add input field, guess button, and feedback display
- [ ] Step 4: Wire up event handlers and game flow

## Files
- Create: `index.html`, `style.css`, `script.js`
- Modify: `README.md`

## Validation
- Open `index.html` in browser
- Enter a number and click Guess
- Verify "too high" / "too low" / "correct" feedback appears
- Play a complete round to verify game ends properly
```

### Guideline Changes

**Remove**:
```
- Prefer more smaller issues (5-8) over fewer large ones (2-3)
- Each issue should be independently implementable when possible
- Each issue must be small enough for Copilot CLI to complete in under 45 minutes
```

**Replace with**:
```
- Target 2-5 issues based on dependency analysis
- Merge tightly-coupled features into one issue
- Keep independent features as separate issues
- Each issue should represent a verifiable functional module
- Include a step-by-step checklist and validation section in each issue
- Each issue should be completable by Copilot CLI within the 55-minute timeout
```

## Example: Number Guessing Game

**Before (6 issues)**:
| # | Issue | Lines Changed |
|---|-------|--------------|
| 1 | Bootstrap skeleton | 251 |
| 2 | Core game loop | 1 |
| 3 | Input validation | 37 |
| 4 | Round-end rules | 4 |
| 5 | localStorage | 4 |
| 6 | Responsive UI + deploy docs | 25 |

Premium cost: 12 requests (6 x implement + 6 x review)

**After (3 issues)**:
| # | Issue | Expected Scope | Validation |
|---|-------|---------------|------------|
| 1 | Skeleton + core logic + input validation | ~250 lines | Open in browser, play a round, verify feedback |
| 2 | Round rules + localStorage + restart | ~80 lines | Exhaust attempts, restart, verify score persists |
| 3 | Responsive UI + deployment | ~50 lines | Resize browser, check mobile layout, verify Pages URL |

Premium cost: 6 requests (3 x implement + 3 x review)

**50% reduction in premium requests, same outcome.**

## Integration Points

| Interface | Format | Changes? |
|-----------|--------|----------|
| AI → `create_issues.py` | JSON `[{title, body}]` | Body content richer, format unchanged |
| Issue body → child Copilot | Plain text via `gh issue view` | Better structured, easier to follow |
| Issue body → review Copilot | Plain text, reads acceptance criteria | Explicit Validation section to check against |
| Event chain | `pull_request:closed` / `pull_request_review:submitted` | No change |

## Risk

Parent repo AI does more work in one session (research + planning). This uses ~1 premium request regardless, and saves multiple premium requests downstream. Net positive.

## Implementation Scope

Only modify: `telegram-bot.md` lines 561-629 (Phase 2 through App Factory guidelines).
Then: `gh aw compile`, commit, push.
