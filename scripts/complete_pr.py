#!/usr/bin/env python3
"""Finish a scoped archive PR only after GitHub reports the required check green."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time

from archive import (ArchiveError, ApiError, CORE_DIRS, DEFAULT_REPO, FULL_SHA,
                     GitHub, existing_content, parse_event, quote, scan_public)


def scoped_pull_request(api, number, expected_sha=None):
    if type(number) is not int or number < 1:
        raise ArchiveError("Invalid pull request number")
    pr = api.request("GET", f"/pulls/{number}")
    head = pr.get("head", {})
    sha = head.get("sha", "")
    branch = head.get("ref", "")
    if expected_sha is not None and sha != expected_sha:
        raise ArchiveError("PR changed since proposal; no merge attempted")
    if pr.get("merged"):
        return pr
    if (pr.get("state") != "open" or pr.get("draft") or
            pr.get("base", {}).get("ref") != "main" or
            head.get("repo", {}).get("full_name") != api.repo or
            not FULL_SHA.fullmatch(sha)):
        raise ArchiveError("PR must be an open, non-draft proposal in this repository")
    files = []
    for page in range(1, 12):
        batch = api.request("GET", f"/pulls/{number}/files?per_page=100&page={page}")
        files.extend(batch)
        if len(batch) < 100:
            break
    else:
        raise ArchiveError("PR is too large to verify completely")
    if not files:
        raise ArchiveError("Empty proposal")
    if branch.startswith("memory/"):
        event_id = branch.removeprefix("memory/")
        expected = f"memory/entries/{event_id}.md"
        if (len(files) != 1 or files[0].get("filename") != expected or
                files[0].get("status") != "added"):
            raise ArchiveError("Automatic memory merge must add exactly its one event")
        text = existing_content(api, expected, sha)
        if text is None or parse_event(text)["event_id"] != event_id:
            raise ArchiveError("Invalid memory event in proposal")
        scan_public(text, "Proposed memory")
    elif re.fullmatch(r"restore/[0-9a-f]{12}-[0-9a-f]{12}", branch):
        for item in files:
            path = item.get("filename", "")
            if path.split("/", 1)[0] not in CORE_DIRS or not path.endswith(".md"):
                raise ArchiveError("Restore changes must remain within the five archive directories")
    else:
        raise ArchiveError("This finisher only merges memory or restore proposals")
    return pr


def finish(api, number, expected_sha=None, wait_seconds=180, dispatch_validation=False):
    pr = scoped_pull_request(api, number, expected_sha)
    if pr.get("merged"):
        return {"status": "already-merged", "number": number, "url": pr["html_url"],
                "merge_commit": pr.get("merge_commit_sha")}
    sha = pr["head"]["sha"]
    branch = pr["head"]["ref"]
    if dispatch_validation:
        api.request("POST", "/actions/workflows/validate.yml/dispatches", {"ref": branch})
    deadline = time.monotonic() + max(0, min(wait_seconds, 600))
    while True:
        checks = api.request("GET", f"/commits/{sha}/check-runs?filter=latest&per_page=100")
        selected = [c for c in checks.get("check_runs", [])
                    if c.get("name") == "archive-validation" and
                    c.get("app", {}).get("slug") == "github-actions"]
        selected.sort(key=lambda c: c.get("id", 0), reverse=True)
        check = selected[0] if selected else None
        if check and check.get("status") == "completed":
            if check.get("conclusion") != "success":
                return {"status": "checks-failed", "number": number, "url": pr["html_url"],
                        "head_commit": sha, "conclusion": check.get("conclusion")}
            latest = api.request("GET", f"/pulls/{number}")
            if latest.get("merged"):
                return {"status": "already-merged", "number": number, "url": pr["html_url"],
                        "merge_commit": latest.get("merge_commit_sha")}
            if latest.get("head", {}).get("sha") != sha:
                raise ArchiveError("PR changed while waiting; no merge attempted")
            try:
                merged = api.request("PUT", f"/pulls/{number}/merge",
                    {"sha": sha, "merge_method": "squash"})
            except ApiError as exc:
                if exc.status in {405, 409, 422}:
                    return {"status": "merge-blocked", "number": number, "url": pr["html_url"],
                            "head_commit": sha, "http_status": exc.status,
                            "reason": "GitHub protection or concurrent changes require reconciliation"}
                raise
            if not merged.get("merged"):
                raise ArchiveError("GitHub did not confirm a merge")
            return {"status": "merged", "number": number, "url": pr["html_url"],
                    "head_commit": sha, "merge_commit": merged.get("sha"),
                    "check_url": check.get("html_url")}
        if time.monotonic() >= deadline:
            return {"status": "checks-pending", "number": number, "url": pr["html_url"],
                    "head_commit": sha}
        time.sleep(min(5, max(0, deadline - time.monotonic())))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--number", type=int, required=True)
    parser.add_argument("--expected-sha")
    parser.add_argument("--wait-seconds", type=int, default=180)
    parser.add_argument("--dispatch-validation", action="store_true")
    args = parser.parse_args()
    try:
        result = finish(GitHub(args.repo), args.number, args.expected_sha,
                        args.wait_seconds, args.dispatch_validation)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] in {"merged", "already-merged"} else 3
    except ArchiveError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

