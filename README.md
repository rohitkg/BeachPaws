# Kent Beach Filter

A static webpage to filter Kent beaches by sand type and dog-friendliness, backed by real data.

## Data sources

- **Beach list, coordinates, sediment types, water quality**: [Environment Agency Bathing Water Quality API](https://environment.data.gov.uk/bwq/) — used under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
- **Dog restrictions**: hand-curated from council Public Spaces Protection Order (PSPO) pages (Thanet, Canterbury, Swale, Dover, Folkestone & Hythe). Each entry in `data/dog_rules.json` records its source URL and the date it was checked. Restrictions change — always check the council page before travelling.

## Files

| File | Role |
|---|---|
| `index.html`, `styles.css`, `app.js` | The site (no build step) |
| `data/config.json` | Districts the pipeline fetches (edit to expand coverage) |
| `data/dog_rules.json` | **Curated** dog restriction data — hand-edited, never written by the pipeline |
| `data/beaches.json` | **Generated** dataset the site loads — output of the pipeline |
| `scripts/build_data.py` | Pipeline: EA API + dog_rules.json → beaches.json |

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

Python 3.9+, stdlib only. Fetches ~35 EA API pages, merges the curated dog rules, and rewrites `data/beaches.json`. Warnings go to stderr (e.g. beaches with no curated dog entry). The script never modifies `dog_rules.json`, and only writes `beaches.json` after every fetch succeeds.
