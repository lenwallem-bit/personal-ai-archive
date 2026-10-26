#!/usr/bin/env python3
"""Event-driven DSH adapter; no polling service, browser, model calls, or new credentials."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

from archive import (ArchiveError, DEFAULT_REPO, GitHub, digest, is_link, load_json,
                     normalize_event, propose_event, read_snapshot, resolve_commit,
                     restore_archive, snapshot_markdown)
from complete_pr import finish


def atomic_json(path, value):
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def atomic_text(path, text):
    if is_link(path) or any(is_link(p) for p in path.parents):
        raise ArchiveError("State paths must not use symlinks or junctions")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    with tmp.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
    os.replace(tmp, path)


@contextmanager
def event_lock(state, event_id):
    """OS advisory lock: released on process exit, no stale lock-file deletion."""
    path = state / "locks" / (event_id + ".lock")
    if is_link(path) or any(is_link(p) for p in path.parents):
        raise ArchiveError("Event locks must not use symlinks or junctions")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if stream.seek(0, 2) == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise ArchiveError("This event_id is being processed; retry the same input later") from None
        try:
            yield
        finally:
            if os.name == "nt":
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def before_task(api, state):
    meta_path = state / "snapshot.json"
    context_path = state / "profile-context.md"
    cached = load_json(meta_path) if meta_path.exists() else None
    valid_cache = bool(cached and cached.get("repository") == api.repo and
                       context_path.is_file() and not is_link(context_path) and
                       digest(context_path.read_text(encoding="utf-8")) == cached.get("sha256"))
    try:
        current = resolve_commit(api)
        if valid_cache and current["sha"] == cached.get("commit"):
            return {"status": "current", **cached, "context_file": str(context_path)}
        snapshot = read_snapshot(api, current["sha"])
        text = snapshot_markdown(snapshot)
        meta = {"repository": api.repo, "commit": snapshot["commit"],
                "documents": len(snapshot["documents"]), "sha256": digest(text)}
        atomic_text(context_path, text)
        atomic_json(meta_path, meta)
        return {"status": "updated", **meta, "context_file": str(context_path)}
    except ArchiveError:
        if valid_cache:
            return {"status": "offline-cache", **cached, "context_file": str(context_path),
                    "warning": "Remote refresh failed; this is the last verified snapshot"}
        raise


def after_task(api, state, event_path, merge=True, wait_seconds=180):
    event = normalize_event(load_json(event_path))
    event_id = event["event_id"]
    with event_lock(state, event_id):
        return publish_locked_event(api, state, event, merge, wait_seconds)


def publish_locked_event(api, state, event, merge, wait_seconds):
    event_id = event["event_id"]
    queue = state / "pending" / (event_id + ".json")
    if queue.exists() and normalize_event(load_json(queue)) != event:
        raise ArchiveError("Local pending event_id has conflicting content")
    atomic_json(queue, event)
    result = propose_event(api, event, publish=True)
    if result["status"] == "pull-request" and merge:
        result = finish(api, result["number"], result.get("commit"), wait_seconds)
    result["event_id"] = event_id
    atomic_json(state / "receipts" / (event_id + ".json"), result)
    if result["status"] in {"merged", "already-merged", "already-present"}:
        queue.unlink(missing_ok=True)
        result["readback"] = before_task(api, state)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--state-dir", type=Path, default=Path(__file__).resolve().parent.parent / ".local" / "dsh")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("before-task")
    after = sub.add_parser("after-task")
    after.add_argument("--input", type=Path, required=True)
    after.add_argument("--no-merge", action="store_true")
    after.add_argument("--wait-seconds", type=int, default=180)
    restore = sub.add_parser("restore")
    restore.add_argument("--sha", required=True)
    restore.add_argument("--publish", action="store_true")
    restore.add_argument("--wait-seconds", type=int, default=180)
    args = parser.parse_args()
    try:
        if is_link(args.state_dir) or any(is_link(p) for p in args.state_dir.parents):
            raise ArchiveError("State directory must be a private regular directory")
        api = GitHub(args.repo)
        if args.command == "before-task":
            result = before_task(api, args.state_dir)
        elif args.command == "after-task":
            result = after_task(api, args.state_dir, args.input, not args.no_merge, args.wait_seconds)
        else:
            result = restore_archive(api, args.sha, args.publish)
            if args.publish and result["status"] == "pull-request":
                result = finish(api, result["number"], result.get("commit"), args.wait_seconds)
                if result["status"] in {"merged", "already-merged"}:
                    result["readback"] = before_task(api, args.state_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 3 if result["status"] in {"checks-failed", "checks-pending", "merge-blocked"} else 0
    except (ArchiveError, OSError) as exc:
        message = str(exc) if isinstance(exc, ArchiveError) else "Local state operation failed"
        print(json.dumps({"status": "error", "error": message}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())

