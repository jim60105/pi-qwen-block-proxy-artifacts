#!/usr/bin/env python3
"""Track C: compare the 240 canonical S* template-row vectors across all
cached Qwen3.8-Flash-Next builds. Reads only those rows (seek+read per row)
out of each build's table tensors; decodes BF16/E4M3; pairwise cosine.

If the EXL3 (BF16) rows decode to the same values as the FP8 builds' rows,
the table is inherited from one common base checkpoint (quantizers did not
retrain it), which is what the README's substrate claim rests on.
"""
import json
import math
import os
import struct

HUB = os.path.expanduser("~/.cache/huggingface/hub")
PREFIX = "model.language_model.layers.1.ple.ple_embedding.ngram_embedding.shard_"
ROWS_PER_TENSOR = 2500012

BUILDS = {
    "EXL3-BF16": "models--wrldsuksgo2mars--Qwen3.8-Flash-Next-EXL3-K4.25-v1",
    "PLE-FP8": "models--wrldsuksgo2mars--Qwen3.8-Flash-Next-EXL3-K4.25-PLE-FP8-v1",
    "NVFP4": "models--nvidia--Qwen3.8-Flash-Next-NVFP4",
}

E4M3 = {}
for b in range(256):
    s = (b >> 7) & 1
    e = (b >> 3) & 0xF
    m = b & 7
    v = (m / 8.0) * 2 ** -6 if e == 0 else float("nan") if (e == 0xF and m == 7) \
        else (1 + m / 8.0) * 2 ** (e - 7)
    E4M3[b] = -v if s else v


def snap(repo):
    d = f"{HUB}/{repo}/snapshots"
    return f"{d}/{os.listdir(d)[0]}/"


def headers(s):
    """tensor name -> (path, hdr_end, data_start) for all table shards."""
    idx = json.load(open(s + "model.safetensors.index.json"))
    wm = idx["weight_map"]
    out = {}
    cache = {}
    for k, f in wm.items():
        if k.startswith(PREFIX) and k.endswith(".weight"):
            if f not in cache:
                p = s + f
                with open(p, "rb") as fh:
                    n = struct.unpack("<Q", fh.read(8))[0]
                    hdr = json.loads(fh.read(n))
                cache[f] = (p, 8 + n, hdr)
            out[k] = cache[f]
    return out


def bf16_to_float(u16):
    return struct.unpack("<f", struct.pack("<I", u16 << 16))[0]


def extract(build_dir, rows):
    s = snap(build_dir)
    tabs = headers(s)
    names = sorted(tabs, key=lambda k: int(k[len(PREFIX):-len(".weight")]))  # NUMERIC shard order
    per = {}
    by_t = {}
    for R in rows:
        by_t.setdefault(R // ROWS_PER_TENSOR, []).append(R)
    for ti, Rlist in sorted(by_t.items()):
        path, hend, hdr = tabs[names[ti]]
        meta = hdr[names[ti]]
        dtype = meta["dtype"]
        cols = meta["shape"][-1]
        base = meta["data_offsets"][0]
        es = 2 if dtype == "BF16" else 1
        with open(path, "rb") as fh:
            for R in Rlist:
                loc = R % ROWS_PER_TENSOR
                fh.seek(hend + base + loc * cols * es)
                raw = fh.read(cols * es)
                if dtype == "BF16":
                    vals = [bf16_to_float(raw[2*i] | (raw[2*i+1] << 8)) for i in range(cols)]
                else:
                    vals = [E4M3[b] for b in raw]
                per[R] = (dtype, vals)
    return per


def cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


S_star = json.load(open("/home/opencode/ple-surgery-regen/tools/g3_S_star.json"))["S_star_final"]
# probe a mix: first 40 canonical rows (host-body + head zones) keeps IO small
probe_rows = S_star[:60] + S_star[len(S_star)//2:len(S_star)//2 + 60] + S_star[-60:]
print(f"probing {len(probe_rows)} of {len(S_star)} S* rows across {len(BUILDS)} builds")

data = {}
for label, repo in BUILDS.items():
    try:
        data[label] = extract(repo, probe_rows)
        dt = {v[0] for v in data[label].values()}
        zero = sum(1 for _, v in data[label].values() if all(x == 0 for x in v))
        print(f"  {label:10s} dtype={dt} zero-rows={zero}")
    except Exception as e:
        print(f"  {label:10s} ERROR {type(e).__name__}: {e}")

labels = list(data)
print("\npairwise on shared rows: exact-equal / cosine min / median")
for i in range(len(labels)):
    for j in range(i + 1, len(labels)):
        A, B = data[labels[i]], data[labels[j]]
        shared = sorted(set(A) & set(B))
        ex = sum(1 for r in shared if A[r][1] == B[r][1])
        cs = sorted(cos(A[r][1], B[r][1]) for r in shared)
        print(f"  {labels[i]:10s} vs {labels[j]:10s} n={len(shared):3d} exact={ex:3d} "
              f"cos min={cs[0]:.6f} med={cs[len(cs)//2]:.6f}")
