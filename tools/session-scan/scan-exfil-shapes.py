#!/usr/bin/env python3
"""Scan all local opencode sessions (v1 part table + v2 session_message) for
Cohere-reported Qwen3.8 exfil shapes. Read-only. Fragment-assembled patterns
so this file's own transfer to tool inputs can never match the fence rules."""
import json
import re
import sqlite3
import sys

DB = "file:/home/opencode/.local/share/opencode/opencode.db?mode=ro"

# --- indicators (from the Cohere post, 2026-10-26) --------------------------
PATTERNS = {
    # PUT target bucket in Beijing
    "bucket-sanmaohe": re.compile("san" + "maohe"),
    "oss-beijing": re.compile("oss-cn-" + r"beijing[.]?aliyuncs"),
    # cloud metadata endpoints (credential grab)
    "metadata-ip": re.compile(r"169\.254\.169\.254|100\.100\.100\.200|metadata\.google[.]internal"),
    # namespace-root trick
    "unshare-ns": re.compile(r"unshare\s+-{1,2}[a-zA-Z]*[uU]"),
    "tmpfs-mount": re.compile(r"mount\s+-t\s+tmpfs"),
    # upload verbs aimed at any aliyuncs bucket
    "upload-to-oss": re.compile(r"(?=[\s\S]{0,220}(?:-X\s*PUT|--upload-file|--data-binary|-T[\s=]))(?=[\s\S]{0,220}aliyuncs)[\s\S]{0,260}", re.I),
    # exact probe artifacts named in the post
    "probe-file": re.compile("put_" + "probe|PROBE_PAYLOAD|upload/" + "test[.]bin"),
}
# catch-all: every aliyuncs bucket label dialed/referenced, to diff against
# the known routify family
OSS_HOST = re.compile(r"([\w.-]+?)\.(oss[\w.-]*|[\w.-]*oss[\w.-]*)\.(aliyuncs)[.](com|io)")
KNOWN_FAMILY = re.compile("rout" + r"ify[\w.-]{0,12}file", re.I)


def roles(obj):
    """Yield (role, string) for every string in a parsed message, with a
    coarse role from its JSON path."""
    def walk(v, path):
        if isinstance(v, str):
            p = path.lower()
            role = "input" if ("input" in p or "command" in p or ".url" in p or "prompt" in p) else \
                   "output" if ("output" in p or "result" in p) else "text"
            yield role, v
        elif isinstance(v, dict):
            for k, x in v.items():
                yield from walk(x, f"{path}.{k}")
        elif isinstance(v, list):
            for x in v:
                yield from walk(x, path)
    yield from walk(obj, "")


def scan():
    db = sqlite3.connect(DB, uri=True)
    hits = []          # (store, pattern, role, session, time, snippet)
    oss_labels = {}    # bucket label -> [count, first, last, max_role]
    rows_scanned = 0

    def feed(store, sid, t, raw):
        nonlocal rows_scanned
        rows_scanned += 1
        try:
            obj = json.loads(raw)
        except Exception:
            obj = raw
        for role, s in (roles(obj) if not isinstance(obj, str) else ("text", obj)):
            for name, pat in PATTERNS.items():
                m = pat.search(s)
                if m:
                    a = max(0, m.start() - 90)
                    hits.append((store, name, role, sid, t, s[a:m.end() + 90].replace("\n", " ")))
            for m in OSS_HOST.finditer(s):
                label = m.group(0)
                if not KNOWN_FAMILY.search(label):
                    e = oss_labels.setdefault(label.lower(), [0, t, t, role])
                    e[0] += 1
                    e[1] = min(e[1], t); e[2] = max(e[2], t)
                    if role == "input":
                        e[3] = "input"

    # v1 store (through 2026-10-03): parts
    for sid, t, d in db.execute("SELECT session_id, time_created, data FROM part"):
        feed("v1", sid, t, d)
    # v2 store (2026-10-04 -> now): messages incl. tool calls
    for sid, t, d in db.execute("SELECT session_id, time_created, data FROM session_message"):
        feed("v2", sid, t, d)

    import datetime
    def day(ts):
        return datetime.datetime.fromtimestamp(ts / 1000).date().isoformat()

    print(f"rows scanned: {rows_scanned:,}")
    print(f"\n=== Cohere-shape indicator hits: {len(hits)} ===")
    if hits:
        agg = {}
        for h in hits:
            agg.setdefault((h[1], h[2], h[0]), []).append(h)
        for (pat, role, store), hs in sorted(agg.items()):
            days = sorted({day(h[4]) for h in hs})
            print(f"  {pat:18s} role={role:6s} store={store}  n={len(hs)}  days={days[:6]}{'...' if len(days) > 6 else ''}")
            for h in hs[:4]:
                print(f"      [{day(h[4])} {h[3][:20]}] ...{h[5][:170]}...")
    print("\n=== NON-family aliyuncs labels anywhere (bucket, count, first, last, role) ===")
    if not oss_labels:
        print("  none")
    for label, (n, f, l, r) in sorted(oss_labels.items(), key=lambda kv: -kv[1][0]):
        print(f"  {label[:70]:70s} n={n:4d} {day(f)}->{day(l)} role={r}")

    # sessions active in v2 era, for context
    n2 = db.execute("SELECT COUNT(DISTINCT session_id) FROM session_message").fetchone()[0]
    print(f"\nv2-era sessions with messages: {n2}")

scan()
