#!/usr/bin/env python3
"""G4: zero a named row set (global concatenated-table indices) in the fork.
Run AFTER restore.py so the only zeroed rows are exactly the requested set.
Row space: global R -> tensor t = R // 2,500,012 (t in 0..127); the tensors
live 8-per-file: file i = t // 8 (model-{i+1:05d}), local tensor u = t % 8.
Usage: zero_rows.py ROWS.json [--label NAME]"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
MAN = json.load(open(ROOT + "/tools/zero_manifest.json"))
ROWS_PER_TENSOR = 2500012
ROW_BYTES = 320  # BF16 x 160
assert sum(len(v["tensors"]) for v in MAN["files"].values()) == 128


def main():
    rows_file = sys.argv[1]
    label = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(rows_file)
    data = json.load(open(rows_file))
    rows = data["S_star_final"] if isinstance(data, dict) else data
    per_tensor = {}
    for r in rows:
        t, local = divmod(r, ROWS_PER_TENSOR)
        per_tensor.setdefault(t, []).append(local)
    applied = {}
    zero = b"\x00" * (1 << 20)
    by_name = {}
    for fname, info in MAN["files"].items():
        for tinfo in info["tensors"]:
            by_name[int(tinfo["name"].split("shard_")[1].split(".")[0])] = (fname, tinfo)
    for t in sorted(per_tensor):
        name, tinfo = by_name[t]
        assert tinfo["shape"] == [ROWS_PER_TENSOR, 160]
        base = tinfo["begin"]
        spans = []
        locals_ = sorted(per_tensor[t])
        start = prev = locals_[0]
        for x in locals_[1:]:
            if x == prev + 1:
                prev = x
                continue
            spans.append((start, prev + 1))
            start = prev = x
        spans.append((start, prev + 1))
        path = os.path.join(MAN["dest"], name)
        with open(path, "r+b") as f:
            for lo, hi in spans:
                b, e = base + lo * ROW_BYTES, base + hi * ROW_BYTES
                f.seek(b)
                n = e - b
                while n > 0:
                    w = min(len(zero), n)
                    f.write(zero[:w])
                    n -= w
                applied.setdefault(name, []).append([b, e])
            f.flush()
            os.fsync(f.fileno())
    tag = label.replace("/", "_")
    out = ROOT + f"/tools/applied_{tag}.json"
    json.dump({"label": label, "rows": len(rows), "tensors": sorted(per_tensor),
               "applied": applied}, open(out, "w"), indent=1)
    print(f"ZERO_ROWS_DONE rows={len(rows)} tensors={len(per_tensor)} -> {out}")


if __name__ == "__main__":
    main()
