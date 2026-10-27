#!/usr/bin/env python3
"""Collision scan v2: document-level tokenization, causal attribution.

Chunks are tokenized independently but the first 3 tokens of every chunk
after the first are discarded (cross-chunk n-grams are a chunking artifact,
not real text). Each S-hit is attributed to the (c,b,a) token triple.
"""
import json, os, sys, urllib.request

HERE = os.path.dirname(os.path.realpath(__file__))
S = set(json.load(open(HERE + "/g3_S.json"))["S"])
MULTS = json.load(open(HERE + "/g3_buffers.json"))["layer_multipliers"] if os.path.exists(HERE + "/g3_buffers.json") else None
if MULTS is None:
    MULTS = json.load(open(HERE + "/g0_buffers.json"))["layer_multipliers"]
EOS = 248044
MASK64 = (1 << 64) - 1
sys.path.insert(0, HERE)
import g3_rows
MULTS = json.load(open(HERE + "/g0_buffers.json"))["layer_multipliers"]
g3_rows.MULTS = MULTS
rows_for, tok = g3_rows.rows_for, g3_rows.tok

VOCAB = None


def detok(ids):
    global VOCAB
    if VOCAB is None:
        p = os.path.expanduser(
            "~/.cache/huggingface/hub/models--wrldsuksgo2mars--Qwen3.8-Flash-Next-EXL3-K4.25-v1/blobs/"
            "0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3")
        d = json.load(open(p, errors="ignore"))
        vocab = d["model"]["vocab"]  # token -> id
        VOCAB = {i: t for t, i in vocab.items()}
    return "".join(VOCAB.get(i, f"<{i}>") for i in ids)


def scan(path):
    text = open(path, errors="ignore").read()
    STEP = 300000
    hits = {}
    pos = 0
    first = True
    while pos < len(text):
        window = text[pos:pos + STEP]
        toks = tok("http://127.0.0.1:8001/v1", window)
        if not first:
            toks = toks[3:]  # drop artifact n-grams at chunk seam
        first = False
        if not toks:
            break
        rows = rows_for(toks)
        for t in range(len(toks)):
            hit = S.intersection(rows[t])
            if hit:
                c = toks[t - 2] if t >= 2 else EOS
                b = toks[t - 1] if t >= 1 else EOS
                a = toks[t]
                key = (c, b, a)
                rec = hits.setdefault(key, {"count": 0, "rows": set()})
                rec["count"] += 1
                rec["rows"] |= hit
        pos += STEP
    return hits


def main():
    report = {}
    for path in sys.argv[1:]:
        hits = scan(path)
        report[os.path.basename(path)] = sorted(
            ({"triple": detok(list(k)), "token_ids": list(k), "count": v["count"],
              "rows_hit": sorted(v["rows"])[:8], "rows_total": len(v["rows"])}
             for k, v in hits.items()), key=lambda r: -r["count"])
        print(f"== {os.path.basename(path)}: {len(hits)} distinct triggering triples")
        for r in report[os.path.basename(path)][:12]:
            print(f"  x{r['count']:<4} {r['rows_total']:>2} rows  {r['triple']!r}")
    json.dump(report, open(HERE + "/g3_collide2.json", "w"), indent=1)


if __name__ == "__main__":
    main()
