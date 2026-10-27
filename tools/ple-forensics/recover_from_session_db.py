#!/usr/bin/env python3
"""Rebuild the PLE forensics directory from the opencode session DB.

The September surgery toolchain was written into a working directory that was
later deleted; every script survived verbatim inside `write` tool-call
arguments in the session database. This replays those writes (and any
subsequent `edit` patches, in chronological order) into a fresh directory.

Usage:  python3 recover_from_session_db.py [DB_PATH] [OUT_DIR] [PATH_FRAGMENT]
Defaults: the local opencode.db, ./recovered, 'ple-surgery-fork'.
"""
import json
import os
import sqlite3
import sys

db_path = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    "~/.local/share/opencode/opencode.db")
out_dir = sys.argv[2] if len(sys.argv) > 2 else "recovered"
fragment = sys.argv[3] if len(sys.argv) > 3 else "ple-surgery-fork"

db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
writes, edits = {}, []
rows = list(db.execute(
    "SELECT data FROM part WHERE data LIKE ? ORDER BY id", (f"%{fragment}%",)))
rows += list(db.execute(
    "SELECT data FROM session_message WHERE data LIKE ? ORDER BY time_created",
    (f"%{fragment}%",)))
for (d,) in rows:
    try:
        parts = json.loads(d)
    except Exception:
        continue
    if not isinstance(parts, list):
        parts = [parts]
    for p in parts:
        if not isinstance(p, dict) or p.get("type") != "tool":
            continue
        inp = (p.get("state") or {}).get("input") or {}
        fp = inp.get("filePath", "")
        if fragment not in fp:
            continue
        if p.get("tool") == "write" and inp.get("content"):
            writes[fp] = inp["content"]
        elif p.get("tool") == "edit" and inp.get("oldString"):
            edits.append(fp)

n = 0
for fp, content in writes.items():
    dest = fp.replace(f"/home/opencode/{fragment}", out_dir)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, "w").write(content)
    n += 1
applied = 0
for fp in edits:
    dest = fp.replace(f"/home/opencode/{fragment}", out_dir)
    if not os.path.exists(dest):
        continue
    src = open(dest).read()
    for (d,) in rows:  # replay in stored order; last matching edit applies
        try:
            parts = json.loads(d)
        except Exception:
            continue
        for p in parts if isinstance(parts, list) else [parts]:
            if not (isinstance(p, dict) and p.get("type") == "tool" and p.get("tool") == "edit"):
                continue
            inp = (p.get("state") or {}).get("input") or {}
            if inp.get("filePath") != fp and inp.get("oldString") not in src:
                continue
            if inp.get("oldString") in src:
                src = src.replace(inp["oldString"], inp.get("newString", ""), 1)
                applied += 1
    open(dest, "w").write(src)
print(f"restored {n} files into {out_dir} ({applied} edit patches replayed)")
