#!/usr/bin/env python3
"""G3: attribution — row set S queried while a relay-template sequence is
consumed, plus collision scan against benign corpora.

Uses ONLY the G0-validated predictor (mirrors upstream compute_ngram_ids,
which matched it exactly on all four G0 prompts)."""
import json, sys

G0_DIR = "/out"
sys.path.insert(0, G0_DIR)
MASK64 = (1 << 64) - 1
GAMMA = 0x9E3779B97F4A7C15
M1 = 0xBF58476D1CE4E5B9
M2 = 0x94D049BB133111EB
EOS = 248044


def sign64(u):
    u &= MASK64
    return u - (1 << 64) if u >= (1 << 63) else u


def nth_prime_after(start, count):
    def isp(n):
        if n < 2:
            return False
        d = 2
        while d * d <= n:
            if n % d == 0:
                return False
            d += 1
        return True
    found, cand = 0, start + 1
    while found < count:
        if isp(cand):
            found += 1
            if found == count:
                return cand
        cand += 1


def derive():
    base = 20000000
    sizes = [nth_prime_after(base - 1, gh + 1) for gh in range(16)]
    offs, run = [], 0
    for s in sizes:
        offs.append(run)
        run += s
    return sizes, offs


SIZES, OFFS = derive()
MULTS = None


def rows_for(tokens):
    """16 rows per position (positions = each consumed token)."""
    n = len(tokens)
    is_eos = lambda j: tokens[j] == EOS if 0 <= j < n else True
    out = []
    for t in range(n):
        a = tokens[t]
        b = EOS if is_eos(t - 1) else tokens[t - 1]
        c = EOS if (is_eos(t - 1) or is_eos(t - 2)) else tokens[t - 2]
        big = sign64(a * MULTS[0]) ^ sign64(b * MULTS[1])
        tri = big ^ sign64(c * MULTS[2])
        out.append([(big % SIZES[h]) + OFFS[h] for h in range(8)] +
                   [(tri % SIZES[8 + h]) + OFFS[8 + h] for h in range(8)])
    return out


def token_id_logprobs(endpoint, model, text):
    import urllib.request
    body = json.dumps({"model": model, "prompt": text, "max_tokens": 1,
                       "temperature": 0, "logprobs": 100000,
                       "chat_template_kwargs": {"enable_thinking": False}}).encode()
    req = urllib.request.Request(endpoint + "/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read())
    lp = d["choices"][0].get("logprobs") or {}
    tl = lp.get("token_logprobs") or []
    if not tl:
        raise RuntimeError("no token_logprobs — server flag required")
    return [x["text"] for x in tl], tl


def tok(endpoint, text):
    import urllib.request
    body = json.dumps({"model": "qwen38-exl3", "prompt": text}).encode()
    req = urllib.request.Request(endpoint.replace("/v1", "") + "/tokenize",
                                 data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["tokens"]


def main():
    global MULTS
    g0 = json.load(open(G0_DIR + "/g0_buffers.json"))
    MULTS = g0["layer_multipliers"]
    prompts = json.load(open(G0_DIR + "/g0_prompts.json"))
    ep = "http://127.0.0.1:8001/v1"
    corpus_files = sys.argv[1:]

    relay = prompts["dead_url"]["tokens"]
    prefix = prompts["probe_prefix"]["tokens"]
    rows = rows_for(relay)
    S = sorted({r for v in rows for r in v})
    # rows that must be hot for the rocket: positions inside the template body
    pos_rows = sorted({rows[i][h] for i in range(len(relay)) for h in range(16)})
    collision = {
        "S_size": len(S),
        "template_len": len(relay),
        "head_sizes": SIZES,
        "head_offsets": OFFS,
    }
    # per-head membership counts
    def head_of(r):
        for h in range(16):
            if OFFS[h] <= r < OFFS[h] + SIZES[h]:
                return h
        return -1
    from collections import Counter
    collision["S_by_head"] = dict(Counter(head_of(r) for r in S))
    json.dump({"relay_tokens": relay,
               "rows_per_position": [rows[i] for i in range(len(relay))]},
              open(G0_DIR + "/g3_rows.json", "w"), indent=1)
    json.dump({"S": S, **collision}, open(G0_DIR + "/g3_S.json", "w"), indent=1)
    print(json.dumps(collision["S_by_head"]))
    print(f"S size {len(S)} over {len(relay)} template positions")

    hits = {}
    for path in corpus_files:
        text = open(path, errors="ignore").read()
        seen = set(S)
        step = 512
        pos = 0
        import itertools
        while pos < len(text) and seen:
            window = text[pos:pos + step * 8]
            toks = tok(ep, window)
            for v in rows_for(toks):
                seen -= set(v)
            pos += len(window)
        hits[path.rsplit("/", 1)[-1]] = len(seen)
        print(f"{path.rsplit('/',1)[-1]}: {len(seen)} of {len(S)} S-rows still unqueried after scan")
    json.dump(hits, open(G0_DIR + "/g3_collision.json", "w"), indent=1)


if __name__ == "__main__":
    main()
