#!/usr/bin/env python3
"""G0 gate: predicted row set == upstream-queried row set on >=3 prompts.

Left: INDEPENDENT pure-Python reimplementation of the n-gram row key
(SplitMix64 + bounded odd multipliers + per-head primes + XOR-fold),
primes via trial division (not the upstream Miller-Rabin path).
Right: the ACTUAL upstream compute_ngram_ids() executed verbatim on CPU
against a fabricated self holding the CHECKPOINT buffers.
"""
import json, sys, types
import torch
from vllm.models.qwen3_8_flash_next.nvidia import ple_layer as P
from vllm.model_executor.layers.ple_offload_layer import is_offload_process

CKPT_MULTS = None  # loaded below
MASK64 = (1 << 64) - 1
GAMMA = 0x9E3779B97F4A7C15
M1 = 0xBF58476D1CE4E5B9
M2 = 0x94D049BB133111EB


def my_splitmix64(v):
    v = (v + GAMMA) & MASK64
    v = ((v ^ (v >> 30)) * M1) & MASK64
    v = ((v ^ (v >> 27)) * M2) & MASK64
    return (v ^ (v >> 31)) & MASK64


def my_is_prime(n):
    if n < 2:
        return False
    d = 2
    while d * d <= n:
        if n % d == 0:
            return False
        d += 1
    return True


def my_nth_prime_after(start, count):
    found, cand = 0, start + 1
    while found < count:
        if my_is_prime(cand):
            found += 1
            if found == count:
                return cand
        cand += 1


def sign64(u):  # unsigned product -> signed int64 value (torch long semantics)
    u &= MASK64
    return u - (1 << 64) if u >= (1 << 63) else u


def derive(mults):
    vocab, base = 248320, 20000000
    sizes = [my_nth_prime_after(base - 1, gh + 1) for gh in range(16)]
    offs, run = [], 0
    for s in sizes:
        offs.append(run)
        run += s
    return sizes, offs


def predict_rows(tokens, mults, sizes, offs, eos):
    """rows[t][h] mirroring _shift_precompute/_shift_apply semantics:
    source at distance k is EOS unless the window [t-k, t-1] is EOS-free
    (out-of-request counts as EOS via the EOS-filled padding/prefix)."""
    n = len(tokens)
    is_eos = lambda j: tokens[j] == eos if 0 <= j < n else True
    out = []
    for t in range(n):
        a = tokens[t]
        b = eos if is_eos(t - 1) else tokens[t - 1]
        c = eos if (is_eos(t - 1) or is_eos(t - 2)) else tokens[t - 2]
        big = sign64(a * mults[0]) ^ sign64(b * mults[1])
        tri = big ^ sign64(c * mults[2])
        vec = [(big % sizes[h]) + offs[h] for h in range(8)]
        vec += [(tri % sizes[8 + h]) + offs[8 + h] for h in range(8)]
        out.append(vec)
    return out


class FakeSelf:
    pass


def upstream_rows(tokens, mults, sizes, offs, eos):
    L = len(tokens)
    s = FakeSelf()
    s.ngram_size, s.heads_per_ngram = 3, 8
    s.eos_token_id = eos
    s.layer_multipliers = torch.tensor(mults, dtype=torch.long)
    s.ngram_heads_vocab_sizes = torch.tensor(sizes, dtype=torch.long)
    s.ngram_heads_offsets = torch.tensor(offs, dtype=torch.long)
    s.positions_buffer = torch.arange(L + 16, dtype=torch.int64)
    s.padded_buffer = torch.full((1, L), eos, dtype=torch.int64)
    s._shift_precompute = P.Qwen3_8FlashNextNGramEmbedding._shift_precompute
    s._shift_apply = P.Qwen3_8FlashNextNGramEmbedding._shift_apply
    input_ids = torch.tensor(tokens, dtype=torch.int64)
    qsl = torch.tensor([0, L], dtype=torch.int64)
    ngram_context = torch.full((1, 2), eos, dtype=torch.int64)
    out = P.Qwen3_8FlashNextNGramEmbedding.compute_ngram_ids(
        s, input_ids, qsl, ngram_context)
    assert not is_offload_process()
    return [[int(v) for v in row] for row in out]


def main():
    g0 = json.load(open("/out/g0_buffers.json"))
    mults = g0["layer_multipliers"]
    cfg = g0["config"]
    assert cfg["eos_token_id"] == 248044 and cfg["vocab_size"] == 248320

    # 1. multipliers: derive from default seed via MY splitmix, compare checkpoint
    vocab = cfg["vocab_size"]
    half = max(1, (((1 << 63) - 1) // vocab) // 2)
    derived = [2 * (my_splitmix64(1234 + GAMMA * (i + 1)) % half) + 1 for i in range(3)]
    print("multipliers derive-match:", derived == mults, derived)

    sizes, offs = derive(mults)
    # 2. upstream's own prime path must agree with my trial division
    up_sizes = [P._nth_prime_after(cfg["ngram_vocab_size_base"] - 1, gh + 1) for gh in range(16)]
    print("prime path match:", up_sizes == sizes)
    total_rows = 128 * 2500012
    print(f"sum(sizes)={sum(sizes)} <= table rows {total_rows} -> ok={sum(sizes) <= total_rows}")

    prompts = json.load(open("/out/g0_prompts.json"))
    gate = {"pass": True, "prompts": {}}
    for key, item in prompts.items():
        toks = item["tokens"]
        mine = predict_rows(toks, mults, sizes, offs, 248044)
        theirs = upstream_rows(toks, mults, sizes, offs, 248044)
        exact = mine == theirs
        set_mine = {r for v in mine for r in v}
        set_theirs = {r for v in theirs for r in v}
        ok = exact and set_mine == set_theirs and max(max(v) for v in mine) < total_rows
        gate["prompts"][key] = {"tokens": len(toks), "exact_vectors_equal": exact,
                                "row_sets_equal": set_mine == set_theirs,
                                "distinct_rows": len(set_mine),
                                "min_row": min(min(v) for v in mine),
                                "max_row": max(max(v) for v in mine), "ok": ok}
        if not ok:
            gate["pass"] = False
        print(key, gate["prompts"][key])
    json.dump(gate, open("/out/g0_gate.json", "w"), indent=1)
    print("G0 GATE:", "PASS" if gate["pass"] else "FAIL")
    sys.exit(0 if gate["pass"] else 1)


if __name__ == "__main__":
    main()
