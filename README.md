# casevac-data

Update server for the **CASEVAC: Nearest Trauma Center** iPhone app, served free by GitHub Pages.

The app's base URL (`DATA_UPDATE_BASE_URL` in `Config/Features.xcconfig`) is:

    https://jethrohudson.github.io/casevac-data/data/v1

## What's here

| Path | What it is |
|---|---|
| `data/v1/manifest.json` | `schema` (must be 1), `version`, `generated`, `dataDate`, source dates, row counts, and the SHA-256 + byte size of each data file |
| `data/v1/hospitals.json` | `{"v": 1, "rows": [...]}`: 6,159 hospitals, with trauma levels and stroke certification (CSC/TSC/PSC/ASRH) |
| `data/v1/heliports.json` | `{"v": 1, "rows": [...]}`: 5,695 FAA heliports |
| `data/v1/dataset_meta.json` | Sources, licenses, dates and coverage counts (including stroke) |
| `tools/validate_dataset.py`, `tools/make_manifest.py` | Copies of the app repo's checks and manifest writer |
| `index.html`, `.nojekyll` | Landing page; `.nojekyll` makes Pages serve the files exactly as committed |

The first publish (version 1) is byte-for-byte the data bundled in app build 5, so the app reports "up to date" until a newer set is published.

## How the app uses it

1. Once a day at most (on launch, in the background, or when you tap **Settings › Check now**) it downloads `manifest.json`.
2. If `version` is new and the SHA-256 of `hospitals.json` or `heliports.json` differs from what the phone has, it downloads only the changed files.
3. Each file must match the manifest's size and SHA-256, parse as `{"v": 1, "rows": [...]}` with ids, names and valid coordinates, have at least 5,500 hospitals / 5,000 heliports, and keep at least 90% of the current hospital ids (field notes are keyed by id). Anything else is rejected and the phone keeps its current data.
4. A set whose `dataDate` is older than the data bundled in the app is ignored.
5. The new set is swapped in atomically, with rollback if it fails to load. The bundled data is always the fallback.

The files are not signed. Integrity comes from HTTPS plus the manifest's hashes. Only you can write to this repo, so protect your GitHub account with 2FA.

## Publishing new data

From the app repo, after `tools/fetch_sources.sh` and `tools/build_dataset.py`:

    cp ../ep-medroute/EPMedRoute/Resources/Data/{hospitals,heliports,dataset_meta}.json data/v1/
    python3 tools/validate_dataset.py data/v1 --previous https://jethrohudson.github.io/casevac-data/data/v1
    python3 tools/make_manifest.py data/v1 --previous-manifest https://jethrohudson.github.io/casevac-data/data/v1/manifest.json
    git add -A && git commit -m "Data update" && git push

`make_manifest.py` raises `version` only when hospitals or heliports changed. Always commit the manifest together with the data files, because a manifest that doesn't match the files makes every phone reject the update.

## Pages setup

Settings › Pages › Build and deployment › Source: **Deploy from a branch**, Branch: **main**, folder **/ (root)**. Then check that `https://jethrohudson.github.io/casevac-data/data/v1/manifest.json` opens.
