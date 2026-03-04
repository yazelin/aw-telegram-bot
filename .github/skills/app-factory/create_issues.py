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

    # Ensure required labels exist (ignore errors if already exist)
    for label, desc, color in [
        ("copilot-task", "Managed by Copilot agent", "0E8A16"),
        ("agent-stuck", "Agent could not complete this issue", "D93F0B"),
        ("needs-human-review", "Needs human intervention", "FBCA04"),
    ]:
        subprocess.run(
            ["gh", "label", "create", label,
             "--repo", repo, "--description", desc, "--color", color],
            capture_output=True, text=True
        )

    for issue in issues:
        result = subprocess.run(
            ["gh", "issue", "create",
             "--repo", repo,
             "--title", issue["title"],
             "--body", issue["body"],
             "--label", "copilot-task"],
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
