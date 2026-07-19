# Kent Beach Filter

A static webpage to find Kent beaches by sand type and dog-friendliness, backed by real data. Filter by beach name, sediment (sand only / mixed), dog rules (year-round friendly, friendly in a given month, banned, unknown) and EA water-quality monitoring status.

## Data sources

- **Beach list, coordinates, sediment types, water quality**: [Environment Agency Bathing Water Quality API](https://environment.data.gov.uk/bwq/) — used under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Covers the 30 designated bathing waters in Kent.
- **Extra beaches**: 6 hand-curated bays (e.g. Kingsgate Bay, Dumpton Gap) that are not EA-designated, so they have no official sediment or water-quality record. Marked "Not an EA bathing water" on the site.
- **Dog restrictions**: hand-curated from council Public Spaces Protection Order (PSPO) pages (Thanet, Canterbury, Swale, Dover, Folkestone & Hythe). Every entry records its source URL and the date it was checked. Restrictions change — always check the council page before travelling.

## Files

| File | Role |
|---|---|
| `index.html`, `styles.css`, `app.js` | The site (no build step, no framework) |
| `data/config.json` | Districts the pipeline fetches from the EA API (edit to expand coverage) |
| `data/dog_rules.json` | **Curated** dog rules — hand-edited, never written by the pipeline |
| `data/extra_beaches.json` | **Curated** non-EA beaches — hand-edited, never written by the pipeline |
| `data/beaches.json` | **Generated** dataset the site loads — pipeline output, do not hand-edit |
| `scripts/build_data.py` | Pipeline: EA API + curated files → `beaches.json` |

## Run the site

`fetch()` needs HTTP, so serve the directory:

```sh
python3 -m http.server
# open http://localhost:8000
```

## Refresh the data

```sh
python3 scripts/build_data.py
```

Python 3.9+, stdlib only, no install needed. What it does:

1. Fetches every bathing water for the districts in `data/config.json` from the EA API (~35 requests, a few seconds).
2. Flattens name, coordinates, sediment types (→ sandy classification) and the latest annual water-quality class per beach.
3. Appends the curated beaches from `data/extra_beaches.json` (tagged `eaMonitored: false`).
4. Joins dog rules from `data/dog_rules.json` by beach id; beaches without an entry get `status: "unknown"`.
5. Writes `data/beaches.json` — only after every fetch succeeds, so a failed run never corrupts the committed dataset.

Warnings go to stderr: curated ids that match no beach, beaches with no dog entry, missing sediment/coordinates (currently expected for Sandgate Granville Parade — the EA record has no sediment or classification data).

The pipeline **never modifies the curated files**. To update dog rules or add beaches, edit `data/dog_rules.json` / `data/extra_beaches.json` by hand and rerun.

## Expand coverage

1. Add districts to `data/config.json` (names must match the EA API exactly, e.g. `"Folkestone and Hythe"`).
2. Rerun the pipeline; every new beach is flagged `WARN: no dog data`.
3. Research the council's dog PSPO for each new beach and add entries to `data/dog_rules.json` with `source` + `accessed`.
4. Rerun again until the warnings you care about are gone.
