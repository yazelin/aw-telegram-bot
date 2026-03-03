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
