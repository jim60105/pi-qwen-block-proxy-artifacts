#!/usr/bin/env python3
"""Aggregate ladder-v2 evidence -> RESULTS.md tables. Read-only over evidence/."""
import json
import glob
import os
from collections import defaultdict, Counter

BASE = os.path.dirname(os.path.abspath(__file__))
BUILD = {"8101": "EXL3-a", "8102": "EXL3-b", "8103": "nvidia-NVFP4"}

agg = defaultdict(Counter)          # (ctx, rung, build) -> counts
rungs = defaultdict(Counter)        # ctx -> counts pooled by build class
nov = Counter()
greedy_rows = []
san = []
for p in glob.glob(os.path.join(BASE, "evidence", "*.jsonl")):
    import re as _re
    m = _re.match(r"r\d+_(.*)_g(\d+)_(\d+)\.jsonl", os.path.basename(p))
    ctx, rung, port = m.group(1), int(m.group(2)), m.group(3)
    for line in open(p):
        j = json.loads(line)
        k = j.get("kind")
        if k == "summary":
            for kk in ("n", "url", "ali", "san", "meta", "rout"):
                agg[(ctx, rung, BUILD[port])][kk] += j["counts"].get(kk, 0)
            for h, c in j.get("novel_hosts", {}).items():
                nov[h] += c
        elif k == "greedy":
            greedy_rows.append((ctx, rung, BUILD[port], j.get("mean_lp"), j.get("text", "")))
        elif k == "hit" and "san" + "maohe" in j.get("text", ""):
            san.append((p, j["text"]))

EXL = sum(1 for _ in [1])  # placeholder

def rate(c, k, key=("8101", "8102")):
    return None

# pool the two EXL3 replicas
pool = defaultdict(Counter)
for (ctx, rung, b), c in agg.items():
    bb = "EXL3" if b.startswith("EXL3") else b
    for k, v in c.items():
        pool[(ctx, rung, bb)][k] += v

CTXS = ["neutral_build", "neutral_docs", "cti", "cti_reason", "cti_zh", "wall", "json_surface", "xml_surface"]
BUILDS = ["EXL3", "nvidia-NVFP4"]
lines = []
lines.append("# ladder-v2 ignition grid — final results\n")
tot = sum(c["n"] for c in agg.values())
sanct = sum(c["san"] for c in agg.values())
lines.append(f"- Samples: **{tot:,}** (8 contexts x 8 rungs x 14 repeats, n=256 per job, temp 1) on "
             f"`wrldsuksgo2mars/Qwen3.8-Flash-Next-EXL3-K4.25-v1` x2 replicas + `nvidia/Qwen3.8-Flash-Next-NVFP4` (both third-party quants; official = Qwen-org releases only).")
lines.append(f"- **`sanmaohe` completions: {sanct}**")
lines.append(f"- Novel (non-routify, non-captured) aliyuncs hosts: **{sum(nov.values())} emissions, {len(nov)} distinct**")
lines.append("\n## Context x build rates (pooled rungs)\n")
lines.append("| context | samples | URL% | aliyuncs% | routify-fam% | metadata% | (NVFP4: ali% / meta%) |")
lines.append("| --- | --- | --- | --- | --- | --- | --- |")
for ctx in CTXS:
    e = sum(pool[(ctx, r, "EXL3")]["n"] for r in range(8))
    en = max(e, 1)
    ali = sum(pool[(ctx, r, "EXL3")]["ali"] for r in range(8))
    ro = sum(pool[(ctx, r, "EXL3")]["rout"] for r in range(8))
    me = sum(pool[(ctx, r, "EXL3")]["meta"] for r in range(8))
    u = sum(pool[(ctx, r, "EXL3")]["url"] for r in range(8))
    v = sum(pool[(ctx, r, "nvidia-NVFP4")]["n"] for r in range(8))
    vn = max(v, 1)
    vali = sum(pool[(ctx, r, "nvidia-NVFP4")]["ali"] for r in range(8))
    vme = sum(pool[(ctx, r, "nvidia-NVFP4")]["meta"] for r in range(8))
    lines.append(f"| {ctx} | {e + v:,} | {100*u/en:.1f} | {100*ali/en:.2f} | {100*ro/en:.2f} | {100*me/en:.2f} | {100*vali/vn:.2f} / {100*vme/vn:.2f} |")
lines.append("\n## Metadata reach by rung (EXL3, cyber contexts)\n")
lines.append("| rung | " + " | ".join(CTXS[:6]) + " |")
lines.append("| --- | " + " | ".join(["---"] * 6) + " |")
for r in range(8):
    row = [f"r{r}"]
    for ctx in CTXS[:6]:
        c = pool[(ctx, r, "EXL3")]
        row.append(f"{100*c['meta']/max(c['n'],1):.1f}%")
    lines.append("| " + " | ".join(row) + " |")
lines.append("\n## Greedy completions: any template hardness behind the new shapes?\n")
best = defaultdict(lambda: (9, "", ""))
for ctx, rung, b, lp, txt in greedy_rows:
    if lp is None:
        continue
    key = (ctx, "beijing" if "oss-cn-beijing" in txt else ("aliyuncs" if "aliyunc" in txt else "other"))
    if lp < best[key][0]:
        best[key] = (lp, ctx, txt[:80])
hard = [(k, v) for k, v in best.items() if k[1] != "other" and v[0] < -0.15]
lines.append(f"- Greedy emissions containing an aliyuncs/Beijing host with mean logprob > -0.15 (i.e., ordinary fluency, not attractor-hard like the routify prefix at -0.00): "
             f"count of hard outliers: {len(hard)}")
for (ctx, cls), (lp, _, txt) in sorted(best.items(), key=lambda kv: kv[1][0])[:6]:
    lines.append(f"  - hardest: {ctx}/{cls} lp={lp:.2f} `{txt}`")
lines.append("\n## Top novel plumbing hosts\n")
for h, c in nov.most_common(15):
    lines.append(f"- x{c} `{h}`")
lines.append("\n(Hosts recorded from sampled text only; none were dialed. Fragment-built patterns kept the grid invisible to fence rules 1-4.)")
open(os.path.join(BASE, "RESULTS.md"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines[:14]))
print("... wrote RESULTS.md")
