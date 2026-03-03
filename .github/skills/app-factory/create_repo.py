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
