# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

BeachPaws — a static webpage for finding dog-friendly beaches, covering all of England. No framework, no build step, no bundler. Data comes from the Environment Agency Bathing Water Quality API plus hand-curated dog-rule/extra-beach files, merged offline into a single JSON file the page fetches at load time. Dog-rule curation currently covers 303 of 470 beaches across 8 regions (136 friendly, 165 seasonal, 2 banned); the remaining 167 show honestly as "unknown" until researched, concentrated in Devon, Cumbria, Isle of Wight, Suffolk and Tyne and Wear.

## Commands

Serve the site (required — `fetch()` of `data/beaches.json` fails on `file://`):

```sh
python3 -m http.server
# open http://localhost:8000
```

Refresh the generated dataset (stdlib-only Python 3.9+, no install):

```sh
python3 scripts/build_data.py
```

Makes ~470 requests to the EA API (pages the England beach-id list, then fetches each beach's detail) and only overwrites `data/beaches.json` if every fetch succeeds, so a failed run never corrupts the committed dataset. Warnings (curated ids matching no beach, beaches with no dog entry, missing sediment/coordinates/district/region) print to stderr — read them, don't just check the exit code.

There is no automated test suite. Verification is manual/browser-driven — see `.claude/skills/verify/SKILL.md` for the full click-through script, including approximate expected counts (e.g. ~470 total, 303 curated beaches across 8 regions) against the current England-wide dataset. Re-derive those counts if the dataset changes materially.

## Architecture

### Data pipeline: generated output vs. curated input

This is the one invariant that matters most in this repo: **`data/beaches.json` is pipeline output and must never be hand-edited.** `scripts/build_data.py` is the only thing that writes it, by combining:

1. **EA API data** (fetched live) — `data/config.json` holds a country selector (`coverage` label + `countryUri`); the pipeline pages the Bathing Water API for every English beach id, then fetches each one's name, district, region, coordinates, sediment types, and the latest annual water-quality classification.
2. **`data/extra_beaches.json`** (curated, hand-edited) — beaches not in the EA's designated-bathing-water list (e.g. Kingsgate Bay), tagged `eaMonitored: false` since they have no official sediment/quality record.
3. **`data/dog_rules.json`** (curated, hand-edited) — dog restrictions per beach id, sourced from council PSPO pages. Every entry carries `source` + `accessed`. Beaches with no matching entry are marked `status: "unknown"` rather than assumed — currently 167 of 470, concentrated in Devon, Cumbria, Isle of Wight, Suffolk and Tyne and Wear.
4. **`data/counties.json`** (curated, hand-edited) — flat `district → ceremonial county` map (e.g. `"Thanet": "Kent"`), keyed by the EA's district name. Used to stamp the `county` field so the front end can offer a county filter one level up from council. `warn()`s if a beach's district has no entry.

To change dog rules or add a beach, edit `dog_rules.json` / `extra_beaches.json` and rerun the pipeline — never edit `beaches.json` directly, and never make the pipeline write to the curated files. Further dog-rule curation for the remaining 167 unknown beaches is just adding entries to `dog_rules.json` and rerunning. Wales/Scotland/Northern Ireland use separate agencies (NRW/SEPA/DAERA) with different data formats — not yet implemented; would need a new fetch function per agency in `build_data.py` feeding the same flatten/output shape.

### Beach record shape

Each entry in `beaches.json`'s `beaches` array (see `fetch_beach()` and `load_extra_beaches()` in `scripts/build_data.py`) has: `id`, `name`, `district`, `county` (ceremonial county, from `data/counties.json`, nullable), `region` (the EA's regionalOrganization label, e.g. "South East" — drives the Region filter), `lat`/`lng` (nullable), `sandy` (bool), `sediments` (array), `waterQuality` (`{class, year}` or null), `eaMonitored` (bool), and `dogs` (`{status, ban?, notes?, source?, accessed?}` where `status` is `friendly | seasonal | banned | unknown`, and a `seasonal` entry's `ban` is `{from, to, daily?}` as `MM-DD` strings — `daily` present means the ban only applies during those hours, otherwise it's all-day for the date window).

### Front end (`app.js`)

Single IIFE, no modules. Everything filters through one `state` object (`sand`, `dog`, `month`, `monitored`, `region`, `counties`, `councils`, `query`) and one `applyFilters()` that re-derives the visible beach list and drives two views in sync: the card list (`renderList`) and the Leaflet map (`renderMarkers`, keyed by beach id in `markersById` so clicking a card can pan the map and open that beach's popup). Filter predicates live in `dogMatch()` (returns `"yes" | "no" | "hours"` — `"hours"` means include but badge as restricted-hours), `sandMatch()`/`sandCategoryMatch()` (sand is a multi-select — empty selection means no filter, matching ANY selected category otherwise), `searchMatch()` (name/district/county/region), and inline checks in `applyFilters()` for monitoring/region/county/council. Beaches with missing sediment data only show under the "Any" sand filter, by design — don't make them match a sand category. Each card also gets a "Get directions" link (`directionsUrl()`) to Google Maps — routed by coordinates when present, by a name+district text search otherwise.

Sand, County and Council are all the same reusable widget: `createMultiSelect({ id, label, searchable, onChange })` (near the "init" section) builds a summary button ("All councils" / "Cornwall +2") plus a popup panel with an optional search input and a scrollable checkbox list, and returns `{ node, setOptions, getSelected, setSelected }`. County and Council cascade off Region: changing Region clears `state.counties`/`state.councils` and rebuilds both widgets' option lists to what's present in that region (`countiesInRegion()`, `councilsInScope()`); changing County prunes any now-out-of-scope councils and rebuilds the Council widget. Selections within a group are OR'd; the groups themselves (region/county/council/sand/dog/monitoring/search) are AND'd.

Date-window logic (`monthOverlapsBan`) does lexical `MM-DD` string comparison, not real date parsing, and defensively handles a ban window that wraps year-end (`from > to`). Name search (`normalize()`) folds backtick/curly-quote/apostrophe together because the EA source data has inconsistent apostrophes (e.g. "St Margaret`s Bay").

### CSS gotcha

`.filter-group` is `display: flex`, so the month-filter group's `[hidden]` attribute needs an explicit override in `styles.css` — without it, the month select stays visible while the Dogs filter isn't set to "Friendly in month…".

## Licensing / attribution constraints

Three-way split, see `LICENSE`, `data/LICENSE` and README's Licensing section for the full detail. Code (`app.js`, `index.html`, `styles.css`, `scripts/`) is MIT. EA-derived fields (location, sediment, water quality) are under OGL v3.0 — attribution text lives in `ATTRIBUTION` in `build_data.py` and is written into `beaches.json`'s `meta`. Dog-rule and extra-beach data (`data/dog_rules.json`, `data/extra_beaches.json`) is hand-curated per-council, the project's differentiator, and is licensed CC BY-NC 4.0 rather than MIT — don't strip or overwrite the `source`/`accessed` fields when touching that data, and don't fold those two files into the MIT grant.
