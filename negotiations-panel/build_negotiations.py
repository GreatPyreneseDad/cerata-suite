#!/usr/bin/env python3
"""
cerata — negotiations display data builder (generic, host-neutral).

Wraps an Index `list_negotiations` export into negotiations-data.js so the
display auto-loads it. ALL classification happens in the browser (index.html),
so this just collects + concatenates pages — no logic, no keys, no network.

Usage:
  # pipe one or more list_negotiations JSON blobs (array, {data:{negotiations}}, or {negotiations}):
  cat page1.json page2.json | python3 build_negotiations.py            # -> negotiations-data.js
  python3 build_negotiations.py page1.json page2.json page3.json       # -> negotiations-data.js
  python3 build_negotiations.py --out mydata.js < all_pages.json

Then: open index.html   (it reads window.RAW_NEGOTIATIONS)
Note: the generated file contains other people's names + reasoning — keep it private (gitignored).
"""
import sys, json, os, re

def extract(blob):
    if isinstance(blob, list):
        return blob
    if isinstance(blob, dict):
        return (blob.get("data", {}) or {}).get("negotiations") or blob.get("negotiations") or []
    return []

def main():
    args = sys.argv[1:]
    out = "negotiations-data.js"
    files = []
    i = 0
    while i < len(args):
        if args[i] == "--out":
            out = args[i + 1]; i += 2
        else:
            files.append(args[i]); i += 1

    negs = []
    texts = []
    if files:
        for f in files:
            texts.append(open(f).read())
    else:
        texts.append(sys.stdin.read())

    for t in texts:
        t = t.strip()
        if not t:
            continue
        # tolerate multiple concatenated JSON objects/arrays in one stream
        decoder = json.JSONDecoder()
        idx = 0
        while idx < len(t):
            t2 = t[idx:].lstrip()
            if not t2:
                break
            try:
                obj, end = decoder.raw_decode(t2)
                negs += extract(obj)
                idx = len(t) - len(t2) + end
            except json.JSONDecodeError:
                break

    # dedupe identical records (same counterparty + turnCount + action), keep richest
    seen = {}
    for n in negs:
        k = (n.get("counterpartyId"), n.get("turnCount"), n.get("latestAction"))
        seen[k] = n
    clean = list(seen.values())
    with open(out, "w") as f:
        f.write("window.RAW_NEGOTIATIONS = " + json.dumps(clean, default=str) + ";\n")
    print(f"{len(negs)} records -> {len(clean)} deduped -> {out} ({os.path.getsize(out)//1024} KB)")

if __name__ == "__main__":
    main()
