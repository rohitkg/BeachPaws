# BeachPaws

A static webpage to find your dog's perfect beach, backed by real data. Filter by beach name, region, sediment (sand only / mixed), dog rules (year-round friendly, friendly in a given month, banned, unknown) and EA water-quality monitoring status. Every beach card links out to Google Maps directions.

Covers **all of England** — every Environment Agency designated bathing water, plus a handful of hand-curated non-designated bays. Dog-rule curation is Kent-only so far; every other beach is honestly badged "Dog rules unknown" until researched. See [Expand coverage](#expand-coverage) for next steps (Wales/Scotland/NI, and curating more councils' dog rules).

## Data sources

- **Beach list, coordinates, sediment types, water quality**: [Environment Agency Bathing Water Quality API](https://environment.data.gov.uk/bwq/) — used under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Covers all ~464 EA-designated bathing waters in England. Each beach also carries a `region` field (the EA's regional-organization grouping, e.g. "South East", "North West") that drives the Region filter.
- **Extra beaches**: 6 hand-curated Kent bays (e.g. Kingsgate Bay, Dumpton Gap) that are not EA-designated, so they have no official sediment or water-quality record. Marked "Not an EA bathing water" on the site.
- **Dog restrictions**: hand-curated from council Public Spaces Protection Order (PSPO) pages — currently Kent only (Thanet, Canterbury, Swale, Dover, Folkestone & Hythe). Every entry records its source URL and the date it was checked. Beaches with no curated entry show "Dog rules unknown" rather than an assumed status. Restrictions change — always check the council page before travelling.
- **Directions**: a "Get directions" link on each card opens Google Maps — routed to the beach's coordinates where known, or a name+district search where coordinates are missing.

## Files

| File | Role |
|---|---|
| `index.html`, `styles.css`, `app.js` | The site (no build step, no framework) |
| `data/config.json` | Country selector the pipeline fetches from the EA API (`coverage` label + `countryUri`) |
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

1. Pages `bathing-water.json` filtered by `data/config.json`'s `countryUri` to collect every English bathing-water id (~470 requests total including per-beach detail fetches; a couple of minutes).
2. Flattens name, district, region, coordinates, sediment types (→ sandy classification) and the latest annual water-quality class per beach.
3. Appends the curated beaches from `data/extra_beaches.json` (tagged `eaMonitored: false`).
4. Joins dog rules from `data/dog_rules.json` by beach id; beaches without an entry get `status: "unknown"`.
5. Writes `data/beaches.json` — only after every fetch succeeds, so a failed run never corrupts the committed dataset.

Warnings go to stderr: curated ids that match no beach, beaches with no dog entry (expected for most of England — dog-rule curation is Kent-only so far), missing sediment/coordinates/district/region.

The pipeline **never modifies the curated files**. To update dog rules or add beaches, edit `data/dog_rules.json` / `data/extra_beaches.json` by hand and rerun.

## Expand coverage

**More dog-rule curation** (same pipeline, no code change): every non-Kent English beach currently shows "Dog rules unknown". Research a council's dog PSPO, add an entry to `data/dog_rules.json` keyed by the beach's EA id with `source` + `accessed`, and rerun.

**Wales / Scotland / Northern Ireland** (not yet implemented): water-quality monitoring is run by separate agencies — Natural Resources Wales (NRW), SEPA (Scotland), DAERA (Northern Ireland) — each with a different data format, and none confirmed to have as clean an API as the EA's. Adding a nation means a new fetch function per agency in `scripts/build_data.py`, plus the same manual council-by-council dog-rule curation. Bigger lift than the England expansion; scope it separately when the time comes.
