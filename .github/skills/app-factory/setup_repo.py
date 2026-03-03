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
