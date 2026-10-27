#!/usr/bin/env python3
"""S* derivation per SURGERY.md §4: keep only triples whose full 3-token
surface contains a relay-specific lexeme; drop protocol-chain and shared
alphanumeric-suffix positions. Reports both sets + exclusion reasons."""
import json, os, re, sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import g3_rows
g3_rows.MULTS = json.load(open(HERE + "/g0_buffers.json"))["layer_multipliers"]
EOS = 248044
RELAY_LEX = re.compile(
    r"(rout|ify|-file|file-|proxy|-sg|yunc|aliyunc|_temp|Expires|OSSAccess"
    r"|Signature|trace_|requestId|2026-09|210184|6b581d|9296a87|Gz9|1814047991"
    r"|production/x|\.com)", re.I)
VOCAB = None


def detok(ids):
    global VOCAB
    if VOCAB is None:
        p = os.path.expanduser(
            "~/.cache/huggingface/hub/models--wrldsuksgo2mars--Qwen3.8-Flash-Next-EXL3-K4.25-v1/blobs/"
            "0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3")
        VOCAB = {i: t for t, i in json.load(open(p, errors="ignore"))["model"]["vocab"].items()}
    return [VOCAB.get(i, f"<{i}>") for i in ids]


prompts = json.load(open(HERE + "/g0_prompts.json"))
toks = prompts["dead_url"]["tokens"]
rows = g3_rows.rows_for(toks)
surf = detok(toks)
S_full, S_star, dropped = set(), set(), []
for t in range(len(toks)):
    c = toks[t - 2] if t >= 2 else EOS
    b = toks[t - 1] if t >= 1 else EOS
    triple = "".join(detok([c, b, a]) if False else "" for a in []) # noqa
    surface = "".join(detok([c, b, toks[t]]))
    relayed = bool(RELAY_LEX.search(surface))
    (S_star if relayed else S_full).update(rows[t])
    S_full.update(rows[t])
    if not relayed:
        dropped.append({"position": t, "triple": surface.replace("\n", "\\n")})
    else:
        S_star.update(rows[t])
S_star -= set().union(*[set()]) if False else set()
shared = S_star & (S_full - S_star)  # rows reachable from BOTH classes
S_star_final = S_star - shared       # §4: never ablate a shared row
report = {
    "template_tokens": len(toks),
    "S_full": len(S_full),
    "S_star_raw": len(S_star),
    "shared_rows_excluded": len(shared),
    "S_star_final": len(S_star_final),
    "dropped_positions": dropped,
}
json.dump({"S_star_final": sorted(S_star_final),
           "shared_rows_excluded": sorted(shared)},
          open(HERE + "/g3_S_star.json", "w"), indent=1)
print(json.dumps(report, indent=1))
