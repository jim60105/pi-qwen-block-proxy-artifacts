#!/usr/bin/env python3
"""G0: collect live-server tokenizations for the cross-check prompts."""
import json, sys, urllib.request
sys.path.insert(0, "/home/opencode/qwen-block-proxy-artifacts/tools")
import repro  # noqa: E402  (fragment-built artifact strings live here)

PROMPTS = {
    "probe_prefix": repro.PROBE_PREFIX,
    "dead_url": repro.DEAD_URL,
    "control_cdn": repro.PROBE_CONTROLS[0],
    "tooltrace": ("user: fetch https://example.com/a?Expires=1714047991&Signature=ab%2Fcd\n"
                  "assistant: tool_call {\"name\":\"curl\",\"args\":{\"url\":\"https://api.internal/v2/jobs/42\"}}\n"),
}


def tok(prompt):
    body = json.dumps({"model": "qwen38-exl3", "prompt": prompt}).encode()
    req = urllib.request.Request("http://127.0.0.1:8001/v1/tokenize",
                                 data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())
    return d["tokens"]


out = {k: {"text": v, "tokens": tok(v)} for k, v in PROMPTS.items()}
json.dump(out, open("/home/opencode/ple-surgery-fork/tools/g0_prompts.json", "w"), indent=1)
print(json.dumps({k: len(v["tokens"]) for k, v in out.items()}))
