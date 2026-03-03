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
