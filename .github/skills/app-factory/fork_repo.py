#!/usr/bin/env python3
"""
Fork a GitHub repository to an organization.

Usage: python fork_repo.py <source_repo> <target_org> [fork_name]
Output: JSON to stdout
  Success: {"ok": true, "repo": "target_org/name", "url": "https://github.com/target_org/name"}
  Failure: {"ok": false, "error": "..."}

Requires: GH_TOKEN with public_repo scope (classic PAT)
"""
import json, subprocess, sys, time

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"ok": False, "error": "Usage: fork_repo.py <source_repo> <target_org> [fork_name]"}))
        sys.exit(1)

    source_repo = sys.argv[1]
    target_org = sys.argv[2]
    fork_name = sys.argv[3] if len(sys.argv) > 3 else None

    cmd = ["gh", "repo", "fork", source_repo,
           "--org", target_org, "--clone=false"]
    if fork_name:
        cmd.extend(["--fork-name", fork_name])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(json.dumps({"ok": False, "error": result.stderr.strip()[-500:]}))
        sys.exit(1)

    # Determine the forked repo name
    name = fork_name if fork_name else source_repo.split("/")[-1]
    repo = f"{target_org}/{name}"

    # Wait for fork to be ready (GitHub needs a moment)
    for i in range(6):
        check = subprocess.run(
            ["gh", "repo", "view", repo, "--json", "name"],
            capture_output=True, text=True
        )
        if check.returncode == 0:
            break
        time.sleep(5)

    print(json.dumps({"ok": True, "repo": repo, "url": f"https://github.com/{repo}"}))

if __name__ == "__main__":
    main()
