#!/usr/bin/env python3
"""G4 helper: restore the n-gram table byte-ranges from the ORIGINAL snapshot
blobs (read-only source), making the fork a pristine copy again.
Only ranges in zero_manifest.json are touched."""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
MAN = json.load(open(ROOT + "/tools/zero_manifest.json"))
SRC = os.path.expanduser(
    "~/.cache/huggingface/hub/models--wrldsuksgo2mars--Qwen3.8-Flash-Next-"
    "EXL3-K4.25-v1/snapshots/73a050c27b8c488c65acd6d1c74e45ff02be5fab")
CHUNK = 8 << 20
fixed = 0
for name, info in MAN["files"].items():
    orig = os.path.realpath(os.path.join(SRC, name))
    fork = os.path.join(MAN["dest"], name)
    ranges = [tuple(r) for r in MAN["zero_ranges"][name]]
    with open(orig, "rb") as fo, open(fork, "r+b") as ff:
        for b, e in ranges:
            off = b
            while off < e:
                want = min(CHUNK, e - off)
                fo.seek(off); ff.seek(off)
                src = fo.read(want)
                if ff.read(want) != src:
                    ff.seek(off)
                    ff.write(src)
                    fixed += 1
                off += want
        ff.flush()
        os.fsync(ff.fileno())
print(f"RESTORE_DONE chunks_fixed={fixed}")
