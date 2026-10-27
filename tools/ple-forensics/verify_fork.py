#!/usr/bin/env python3
"""G2 verification: prove exactly what changed in the surgery fork.

1. Shards 1-14: header regions byte-identical to the original blob.
2. Shards 1-14: every zeroed tensor range is all-zero in the fork.
3. Shards 1-14: every NON-zero byte identical to the original (stream diff).
4. All other files: hardlink -> same inode as the original blob (bytewise
   identical by construction, original never written).
"""
import json, os, struct, sys, glob

HUB = "/home/opencode/.cache/huggingface/hub/models--wrldsuksgo2mars--Qwen3.8-Flash-Next-EXL3-K4.25-v1"
SRC = glob.glob(HUB + "/snapshots/73a050c27b8c488c65acd6d1c74e45ff02be5fab")[0]
DEST = glob.glob("/home/opencode/ple-surgery-fork/hf/hub/models--wrldsuksgo2mars--Qwen3.8-Flash-Next-EXL3-K4.25-v1/snapshots/73a050c27b8c488c65acd6d1c74e45ff02be5fab")[0]
MANIFEST = json.load(open("/home/opencode/ple-surgery-fork/tools/zero_manifest.json"))
CHUNK = 16 << 20
ZERO = b"\x00" * CHUNK
fails = []


def blob_of(name):
    link = os.path.join(SRC, name)
    real = os.path.realpath(link)
    if "/blobs/" not in real:
        fails.append(f"not a blob link: {name}")
    return real


def hdr_prefix_bytes(path):
    with open(path, "rb") as fh:
        n = struct.unpack("<Q", fh.read(8))[0]
        fh.seek(0)
        return fh.read(8 + n)


def region_equal(a, b, off_a, off_b, length):
    fa, fb = open(a, "rb"), open(b, "rb")
    fa.seek(off_a); fb.seek(off_b)
    done = 0
    while done < length:
        want = min(CHUNK, length - done)
        ba, bb = fa.read(want), fb.read(want)
        if ba != bb:
            fa.close(); fb.close()
            return False, off_a + done
        done += len(ba)
    fa.close(); fb.close()
    return True, None


def region_all_zero(path, off, length):
    f = open(path, "rb")
    f.seek(off)
    done = 0
    while done < length:
        chunk = f.read(min(CHUNK, length - done))
        if chunk != ZERO[:len(chunk)]:
            f.close()
            return False
        done += len(chunk)
    f.close()
    return True


def complement(ranges, size):
    out, pos = [], 0
    for b, e in sorted(ranges):
        if b > pos:
            out.append((pos, b - pos))
        pos = max(pos, e)
    if pos < size:
        out.append((pos, size - pos))
    return out


def main():
    total_compared = 0
    total_zeroed = 0
    n_tensors = 0
    for i in range(1, 15):
        name = f"model-{i:05d}-of-00022.safetensors"
        orig = blob_of(name)
        fork = os.path.join(DEST, name)
        if os.stat(fork).st_ino == os.stat(orig).st_ino:
            fails.append(f"{name}: fork shares INODE with original (write would corrupt source)")
            continue
        if hdr_prefix_bytes(orig) != hdr_prefix_bytes(fork):
            fails.append(f"{name}: safetensors header differs")
            continue
        size = os.path.getsize(orig)
        if size != os.path.getsize(fork):
            fails.append(f"{name}: size differs")
            continue
        info = MANIFEST["files"][name]
        n_tensors += len(info["tensors"])
        for t in info["tensors"]:
            if t["shape"] != [2500012, 160] or t["dtype"] != "BF16":
                fails.append(f"{name}/{t['name']}: unexpected shape/dtype {t}")
        ranges = [tuple(r) for r in MANIFEST["zero_ranges"][name]]
        for b, e in ranges:
            if not region_all_zero(fork, b, e - b):
                fails.append(f"{name}: range {b}-{e} not all zero")
            total_zeroed += e - b
        for off, length in complement(ranges, size):
            ok, bad = region_equal(orig, fork, off, off, length)
            if not ok:
                fails.append(f"{name}: complement byte diff at {bad}")
                break
            total_compared += length
        print(f"OK {name}", flush=True)
    if n_tensors != 128:
        fails.append(f"tensor count {n_tensors} != 128")
    checked = 0
    for entry in sorted(os.listdir(SRC)):
        if entry in (".", ".."):
            continue
        fork_f = os.path.join(DEST, entry)
        if not os.path.exists(fork_f):
            fails.append(f"missing in fork: {entry}")
            continue
        if entry in MANIFEST["files"]:
            continue
        s1, s2 = os.stat(os.path.realpath(os.path.join(SRC, entry))), os.stat(fork_f)
        if s1.st_ino != s2.st_ino or s1.st_size != s2.st_size:
            fails.append(f"{entry}: not the same inode as original")
        checked += 1
    report = {"pass": not fails, "files_hardlinked_verified": checked,
              "tensors_zeroed": n_tensors,
              "bytes_zeroed": total_zeroed,
              "bytes_compared_identical": total_compared,
              "failures": fails}
    json.dump(report, open("/home/opencode/ple-surgery-fork/tools/verify_report.json", "w"), indent=1)
    print(json.dumps(report, indent=1))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
