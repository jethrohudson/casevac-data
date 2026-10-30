#!/usr/bin/env python3
"""
Write manifest.json for the daily data publish and decide whether anything changed.

usage: make_manifest.py <dir> [--previous-manifest <url-or-path>]
Writes <dir>/manifest.json and prints changed=true|false (also to $GITHUB_OUTPUT).

manifest.json:
  {"schema": 1, "version": <int, previous+1 when data changes>, "generated": ISO-8601,
   "dataDate": newest source date, "sources": {...dates...},
   "counts": {"hospitals": n, "heliports": n},
   "files": {"hospitals.json": {"sha256": hex, "size": bytes}, ...}}
"changed" compares hospitals.json and heliports.json hashes only; dataset_meta.json carries
build dates that change every run and is not a reason to publish.
"""
import hashlib, json, os, sys, time, urllib.request

FILES = ["hospitals.json", "heliports.json", "dataset_meta.json"]
DATA_FILES = ["hospitals.json", "heliports.json"]

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()

def load_prev(src):
    try:
        if src.startswith("http"):
            with urllib.request.urlopen(src, timeout=30) as r: return json.load(r)
        return json.load(open(src))
    except Exception as e:
        print(f"(no previous manifest: {e})", file=sys.stderr); return None

def main():
    d = sys.argv[1]
    prev = load_prev(sys.argv[sys.argv.index("--previous-manifest") + 1]) if "--previous-manifest" in sys.argv else None
    meta = json.load(open(os.path.join(d, "dataset_meta.json")))
    src = meta.get("sources", {})
    dates = {
        "hifld": src.get("hifld", {}).get("dataAsOf"),
        "cms": src.get("cms", {}).get("modified"),
        "faa": src.get("faa", {}).get("effective"),
        "osm": src.get("osm", {}).get("snapshot"),
    }
    files = {n: {"sha256": sha(os.path.join(d, n)), "size": os.path.getsize(os.path.join(d, n))} for n in FILES}
    changed = prev is None or any(prev.get("files", {}).get(n, {}).get("sha256") != files[n]["sha256"] for n in DATA_FILES)
    counts = {n.split(".")[0]: len(json.load(open(os.path.join(d, n)))["rows"]) for n in DATA_FILES}
    manifest = {
        "schema": 1,
        "version": (int(prev.get("version", 0)) + 1) if (prev and changed) else (int(prev["version"]) if prev else 1),
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        # Settings shows this: the newest of the clinical source dates (CMS / HIFLD / FAA).
        "dataDate": max([v for k, v in dates.items() if v and k != "osm"] or [meta.get("built")]),
        "sources": dates,
        "counts": counts,
        "files": files,
    }
    json.dump(manifest, open(os.path.join(d, "manifest.json"), "w"), indent=1)
    print(json.dumps(manifest, indent=1))
    print(f"changed={'true' if changed else 'false'}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f: f.write(f"changed={'true' if changed else 'false'}\n")

if __name__ == "__main__":
    main()
