#!/usr/bin/env python3
"""
Sanity checks that BLOCK a bad publish (exit 1). Mirrors the checks the app runs before it swaps
data in (DataUpdatePlanner.validate), so a file the server accepts is a file the app accepts.

usage: validate_dataset.py <dir> [--previous <dir-or-url-with-manifest-and-files>]
  - hospitals.json >= 5,500 rows, heliports.json >= 5,000 rows
  - schema: {"v": 1, "rows": [...]}, every row has string id, name, lat/lon in range
  - ids unique (field notes are keyed by hospital id)
  - id stability vs the previous publish: at most 10% of previous hospital ids may disappear
"""
import json, os, sys, urllib.request

MIN_ROWS = {"hospitals.json": 5500, "heliports.json": 5000}
MAX_ID_LOSS = 0.10

def load(src, name):
    if src.startswith("http"):
        with urllib.request.urlopen(src.rstrip("/") + "/" + name, timeout=60) as r:
            return json.load(r)
    return json.load(open(os.path.join(src, name)))

def check_rows(name, doc):
    errs = []
    if not isinstance(doc, dict) or doc.get("v") != 1 or not isinstance(doc.get("rows"), list):
        return [f"{name}: expected {{'v': 1, 'rows': [...]}}"]
    rows = doc["rows"]
    if len(rows) < MIN_ROWS[name]:
        errs.append(f"{name}: {len(rows)} rows < minimum {MIN_ROWS[name]}")
    ids = set()
    for i, r in enumerate(rows):
        rid = r.get("id")
        if not isinstance(rid, str) or not rid:
            errs.append(f"{name}[{i}]: missing id"); continue
        if rid in ids: errs.append(f"{name}: duplicate id {rid}")
        ids.add(rid)
        if not isinstance(r.get("n"), str): errs.append(f"{name}[{rid}]: missing name")
        la, lo = r.get("la"), r.get("lo")
        if not isinstance(la, (int, float)) or not isinstance(lo, (int, float)) or not (-90 <= la <= 90) or not (-180 <= lo <= 180):
            errs.append(f"{name}[{rid}]: bad coordinate")
        if name == "hospitals.json" and "er" in r and not isinstance(r["er"], bool):
            errs.append(f"{name}[{rid}]: er must be bool")
        if len(errs) > 25: break
    return errs

def main():
    d = sys.argv[1]
    prev = sys.argv[sys.argv.index("--previous") + 1] if "--previous" in sys.argv else None
    errs = []
    docs = {}
    for n in MIN_ROWS:
        try:
            docs[n] = load(d, n)
            errs += check_rows(n, docs[n])
        except Exception as e:
            errs.append(f"{n}: unreadable ({e})")
    try:
        meta = load(d, "dataset_meta.json")
        if not isinstance(meta.get("sources"), dict) or "built" not in meta:
            errs.append("dataset_meta.json: missing sources/built")
    except Exception as e:
        errs.append(f"dataset_meta.json: unreadable ({e})")
    if prev and not errs:
        try:
            old = {r["id"] for r in load(prev, "hospitals.json")["rows"]}
            new = {r["id"] for r in docs["hospitals.json"]["rows"]}
            lost = len(old - new) / max(1, len(old))
            print(f"id stability: {len(old - new)} of {len(old)} previous hospital ids gone ({lost:.1%})")
            if lost > MAX_ID_LOSS:
                errs.append(f"hospital ids: {lost:.1%} of previous ids disappeared (> {MAX_ID_LOSS:.0%}); field notes would orphan")
        except Exception as e:
            print(f"(no previous publish to compare: {e})")
    if errs:
        print("VALIDATION FAILED:"); [print("  -", e) for e in errs[:50]]
        sys.exit(1)
    print("validation ok:", {n: len(docs[n]["rows"]) for n in docs})

if __name__ == "__main__":
    main()
