# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

BeachPaws helps people plan better beach days with dog-access and water-quality information. It covers every Environment Agency-designated bathing water in England, plus carefully curated non-designated beaches. The 470-beach dataset contains all 464 EA-designated bathing waters in England plus 6 explicitly curated extras; it does not claim to list every named beach in England. It is a static webpage with no framework, build step or bundler. Data comes from the Environment Agency Bathing Water Quality API plus hand-curated dog-rule/extra-beach files, merged offline into a single JSON file the page fetches at load time. Dog-rule curation currently covers 303 beaches (136 friendly, 165 seasonal, 2 banned) across 18 counties in five EA regional-organization areas; the remaining 167 show honestly as "unknown" until researched, concentrated in Devon, Cumbria, Isle of Wight, Suffolk and Tyne and Wear.

Style convention: do not use Unicode em dashes in comments, documentation, metadata or user-facing copy. Use suitable punctuation such as commas, colons, parentheses, semicolons or sentence breaks instead.

## Commands

Serve the site (required because `fetch()` of `data/beaches.json` fails on `file://`):

```sh
python3 -m http.server
# open http://localhost:8000
```

Refresh the generated dataset (stdlib-only Python 3.9+, no install):

```sh
python3 scripts/build_data.py
```

Makes ~470 requests to the EA API (pages the England beach-id list, then fetches each beach's detail) and only overwrites `data/beaches.json` if every fetch succeeds, so a failed run never corrupts the committed dataset. Warnings (curated ids matching no beach, beaches with no dog entry, missing sediment/coordinates/district/region) print to stderr. Read them, not just the exit code.

Run the complete repository checks, including the Node predicate tests:

```sh
./scripts/check.sh
```

Browser verification is still manual; see `.claude/skills/verify/SKILL.md` for the full click-through script, including approximate expected counts (464 EA-designated bathing waters + 6 curated extras = 470 total; 303 dog-rule entries) against the current England-wide dataset. Re-derive those counts if the dataset changes materially.

After every implementation, spawn a dedicated QA agent before declaring the work complete. The QA agent must run the full repository checks, start the local static server, and validate both the changed behavior and relevant regressions in an actual browser, including checking the browser console for errors. New or changed behavior must receive focused browser validation in addition to the broader regression pass.

## Architecture

### Data pipeline: generated output vs. curated input

This is the one invariant that matters most in this repo: **`data/beaches.json` is pipeline output and must never be hand-edited.** `scripts/build_data.py` is the only thing that writes it, by combining:

1. **EA API data** (fetched live): `data/config.json` holds a country selector (`coverage` label + `countryUri`); the pipeline pages the Bathing Water API for every English beach id, then fetches each one's name, district, region, coordinates, sediment types, and the latest annual water-quality classification.
2. **`data/extra_beaches.json`** (curated, hand-edited): beaches not in the EA's designated-bathing-water list (e.g. Kingsgate Bay), tagged `eaMonitored: false` since they have no official sediment/quality record.
3. **`data/dog_rules.json`** (curated, hand-edited): dog restrictions per beach id, sourced from council PSPO pages. Every entry carries `source` + `accessed`. Beaches with no matching entry are marked `status: "unknown"` rather than assumed. There are currently 167 unknown beaches, concentrated in Devon, Cumbria, Isle of Wight, Suffolk and Tyne and Wear.
4. **`data/counties.json`** (curated, hand-edited): flat `district → ceremonial county` map (e.g. `"Thanet": "Kent"`), keyed by the EA's district name. Used to stamp the `county` field so the front end can offer a county filter one level up from council. `warn()`s if a beach's district has no entry.

To change dog rules or add a beach, edit `dog_rules.json` / `extra_beaches.json` and rerun the pipeline. Never edit `beaches.json` directly or make the pipeline write to curated files. Further dog-rule curation for the remaining 167 unknown beaches is just adding entries to `dog_rules.json` and rerunning. Wales/Scotland/Northern Ireland use separate agencies (NRW/SEPA/DAERA) with different data formats. They are not yet implemented and would need a new fetch function per agency in `build_data.py` feeding the same flatten/output shape.

### Beach record shape

Each entry in `beaches.json`'s `beaches` array (see `fetch_beach()` and `load_extra_beaches()` in `scripts/build_data.py`) has: `id`, `name`, `district`, `county` (ceremonial county, from `data/counties.json`, nullable), `region` (the EA's regionalOrganization label, e.g. "South East", which drives the Region filter), `lat`/`lng` (nullable), `sandy` (bool), `sediments` (array), `waterQuality` (`{class, year}` or null), `eaMonitored` (bool), and `dogs` (`{status, ban?, notes?, source?, accessed?}` where `status` is `friendly | seasonal | banned | unknown`, and a `seasonal` entry's `ban` is `{from, to, daily?}` as `MM-DD` strings. `daily` means the ban applies only during those hours; otherwise it applies all day for the date window).

### Front end (`core.js`, `app.js`)

The page has no build step or browser modules. `core.js` uses a small UMD wrapper to expose the pure filter predicates as `window.BeachPawsCore` in the browser and `module.exports` in Node tests. `app.js` keeps UI state, DOM work and Leaflet integration in a single IIFE. Everything filters through one `state` object (`sand`, `dog`, `month`, `monitored`, `region`, `counties`, `councils`, `query`) and one `applyFilters()` that re-derives the visible beach list and drives two views in sync: the card list (`renderList`) and the Leaflet map (`renderMarkers`, keyed by beach id in `markersById` so clicking a card can pan the map and open that beach's popup). Core predicates include `dogMatch()` (returns `"yes" | "no" | "hours"`; `"hours"` means include but badge as restricted-hours), `sandMatch()`/`sandCategoryMatch()` (sand is a multi-select: an empty selection means no filter, matching any selected category otherwise), and `searchMatch()` (name/district/county/region). Inline checks in `applyFilters()` handle monitoring/region/county/council. Beaches with missing sediment data only show under the "Any" sand filter, by design. Do not make them match a sand category. Each card also gets a "Get directions" link (`directionsUrl()`) to Google Maps, routed by coordinates when present or a name+district text search otherwise.

Sand, County and Council are all the same reusable widget: `createMultiSelect({ id, label, searchable, onChange })` (near the "init" section) builds a summary button ("All councils" / "Cornwall +2") plus a popup panel with an optional search input and a scrollable checkbox list, and returns `{ node, setOptions, getSelected, setSelected }`. County and Council cascade off Region: changing Region clears `state.counties`/`state.councils` and rebuilds both widgets' option lists to what's present in that region (`countiesInRegion()`, `councilsInScope()`); changing County prunes any now-out-of-scope councils and rebuilds the Council widget. Selections within a group are OR'd; the groups themselves (region/county/council/sand/dog/monitoring/search) are AND'd.

Date-window logic (`monthOverlapsBan`) does lexical `MM-DD` string comparison, not real date parsing, and defensively handles a ban window that wraps year-end (`from > to`). Name search (`normalize()`) folds backtick/curly-quote/apostrophe together because the EA source data has inconsistent apostrophes (e.g. "St Margaret`s Bay").

### Design system / CSS gotchas

`styles.css` opens with a design-token layer (`:root` custom properties for colors, type, spacing and radii); component rules consume tokens, so restyle by changing tokens, not scattering new hexes. Full reference including breakpoints (≥900px two-column, ≤700px collapsed filters) lives in `docs/DESIGN.md`. The four dog-status colors are duplicated in `app.js`'s `STATUS_COLORS` (Leaflet markers), so change both together.

Gotchas: `.filter-group` is `display: flex`, so the month-filter group's `[hidden]` attribute needs an explicit override in `styles.css`; without it, the month select stays visible while the Dogs filter isn't set to "Friendly in month…". Leaflet inlines `position: relative` on a `position: static` map container, so the stacked breakpoint must reset `top: auto` on `#map` or the base sticky `top: 90px` re-applies as a relative offset. The sticky filter bar needs `z-index` above 1000 because Leaflet's controls compete globally once `#map` is static on small screens.

## Licensing / attribution constraints

Three-way split, see `LICENSE`, `data/LICENSE` and README's Licensing section for the full detail. Code (`core.js`, `app.js`, `index.html`, `styles.css`, `scripts/`, `tests/`) is MIT. EA-derived fields (location, sediment, water quality) are under OGL v3.0. Attribution text lives in `ATTRIBUTION` in `build_data.py` and is written into `beaches.json`'s `meta`. Dog-rule and extra-beach data (`data/dog_rules.json`, `data/extra_beaches.json`) is hand-curated per-council, the project's differentiator, and is licensed CC BY-NC 4.0 rather than MIT. Do not strip or overwrite the `source`/`accessed` fields when touching that data, and do not fold those two files into the MIT grant.
