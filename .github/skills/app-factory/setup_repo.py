#!/usr/bin/env python3
"""
Push initial files to a newly created repo.

Usage: python setup_repo.py <owner/name> <json_files>
  json_files: JSON string of [{"path": "relative/path", "content": "file content"}, ...]
Output: JSON to stdout
  Success: {"ok": true, "files_pushed": 5}
  Failure: {"ok": false, "error": "..."}
"""
import json, os, subprocess, sys, tempfile, time

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"ok": False, "error": "Usage: setup_repo.py <owner/name> <json_files>"}))
        sys.exit(1)

    repo = sys.argv[1]
    files = json.loads(sys.argv[2])

    with tempfile.TemporaryDirectory() as tmpdir:
        # Clone the empty repo (retry for newly created repos that aren't ready yet)
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            result = subprocess.run(
                ["gh", "repo", "clone", repo, tmpdir, "--", "--depth=1"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                break
            if attempt < max_attempts:
                time.sleep(5)
        else:
            print(json.dumps({"ok": False, "error": f"Clone failed after {max_attempts} attempts: {result.stderr.strip()[-300:]}"}))
            sys.exit(1)

        # Write files
        for f in files:
            filepath = os.path.join(tmpdir, f["path"])
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as fh:
                fh.write(f["content"])

        # Git add, commit, push (use gh auth token for push authentication)
        token = os.environ.get("FACTORY_PAT") or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
        subprocess.run(["git", "remote", "set-url", "origin",
                       f"https://x-access-token:{token}@github.com/{repo}.git"],
                       cwd=tmpdir, capture_output=True)
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
