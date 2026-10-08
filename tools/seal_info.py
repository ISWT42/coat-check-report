#!/usr/bin/env python3
"""Read-only helper: print the seal facts of a sealed list file.

Usage: python tools/seal_info.py <path/to/LIST-SHA256.txt>

It reads <list>, <list>.tsr (FreeTSA time, via the local openssl) and
<list>.ots (Bitcoin block height, if the proof already carries one).
It makes no network call and changes nothing. Bitcoin heights come from
the attestation bytes in the .ots file; it does NOT verify the proof.
Use `ots verify` for that (see the Appendix of the report).
"""
import hashlib, subprocess, sys, re, os

BTC_TAG = bytes.fromhex("0588960d73d71901")
PENDING_TAG = bytes.fromhex("83dfe30d2ef90c8e")


def varuint(b, i):
    n = 0
    shift = 0
    while True:
        c = b[i]
        i += 1
        n |= (c & 0x7F) << shift
        if not c & 0x80:
            return n, i
        shift += 7


def ots_heights(path):
    if not os.path.exists(path):
        return None, 0
    b = open(path, "rb").read()
    heights, pending, i = [], 0, 0
    while True:
        j = b.find(BTC_TAG, i)
        if j < 0:
            break
        try:
            _len, k = varuint(b, j + 8)
            h, _ = varuint(b, k)
            heights.append(h)
        except Exception:
            pass
        i = j + 8
    pending = b.count(PENDING_TAG)
    return sorted(set(heights)), pending


def tsr_time(path):
    if not os.path.exists(path):
        return None
    out = subprocess.run(["openssl", "ts", "-reply", "-in", path, "-text"],
                         capture_output=True, text=True).stdout
    m = re.search(r"Time stamp: (.*)", out)
    return m.group(1).strip() if m else None


def main(p):
    data = open(p, "rb").read()
    print("file:", p)
    print("sha256:", hashlib.sha256(data).hexdigest())
    base = p[:-4] if p.endswith(".txt") else p
    tsr = p + ".tsr" if os.path.exists(p + ".tsr") else base + ".tsr"
    print("freetsa:", tsr_time(tsr))
    h, pend = ots_heights(p + ".ots")
    print("bitcoin_blocks_in_file:", h, "pending_calendar_attestations:", pend)


if __name__ == "__main__":
    for a in sys.argv[1:]:
        main(a)
