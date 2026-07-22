---
name: verify
description: How to run and verify the BeachPaws site end-to-end.
---

# Verify BeachPaws

No build step. Surface = browser GUI.

1. Serve: `python3 -m http.server 8741` from repo root (fetch of
   `data/beaches.json` fails on `file://`).
2. Open `http://localhost:8741` in the browser (claude-in-chrome works).
3. Header tag reads "England"; footer "Dataset generated ... · N beaches"
   line matches `data.meta.beachCount`.
4. Drive the filters (counts below are approximate — the EA dataset can
   drift a few beaches release to release; re-derive if `beachCount`
   in `data/beaches.json`'s `meta` differs meaningfully from ~470):
   - Total ≈ 464 EA-designated bathing waters + 6 curated extras ≈ 470.
   - Sand is a multi-select (popup with checkboxes: Sand only,
     Sand + shingle, Sand + rock, Sand + mud). None checked = Any.
     Checking "Sand only" ≈ 201; adding "Sand + rock" ≈ 261 (options
     OR within the group). Beaches with no/other sediment show only
     when nothing is checked.
   - Region → County → Council cascade. Region is a single-select
     driving the other two; County and Council are searchable
     multi-select popups. Region "Any" lists every distinct `region`
     (EA regionalOrganization areas: South East, South West, North
     West, North East, Anglian, Midlands). Selecting a region (e.g.
     South West ≈ 211) narrows the County list to that region's
     counties and the Council list to its districts; picking counties
     (e.g. Devon ≈ 67) narrows Council to that county's districts
     (East Devon, South Hams, Torbay…). Changing Region clears the
     County + Council selections. All three views (list, map, count)
     stay in sync.
   - Search a Kent beach name (e.g. "margate" or "margaret's" — the
     latter checks backtick-normalization against the EA's "St
     Margaret`s Bay") → still finds the curated Kent entry with its
     colored dog badge (green/amber/red) and a working source link.
   - Search a non-Kent beach (e.g. "spittal" or "blackpool") → grey
     "Dog rules unknown" badge — expected for the ~434 beaches outside
     the currently-curated Kent set.
   - Search matches `name`, `district`, `county` and `region` (not
     just the name): "kent" → 36 beaches whose county is Kent, incl.
     ones with no "kent" in the name (e.g. "Herne Bay", "Tankerton").
   - Water monitoring "Not monitored" → 6 (the curated extras, all
     Thanet); "EA-monitored" → the rest. "?" button toggles the
     designation explainer (works pre-data-load; listener bound
     outside initControls).
   - Reset filters button → all controls (Sand, Region, County,
     Council, Dogs, Water monitoring, Search) back to Any/empty, full
     count shown.
5. "Get directions" on a card: opens a new tab to
   `google.com/maps/dir/?api=1&destination=<lat>,<lng>` for a beach
   with coordinates, or the `google.com/maps/search/...` fallback for
   a coords-null beach (e.g. Sandgate Granville Parade). Clicking it
   must **not** pan the map (the card's click handler bails on
   `ev.target.tagName === "A"`); clicking elsewhere on the card still
   pans the map and opens the marker popup.
6. Data refresh: `python3 scripts/build_data.py` — pages the whole EA
   England dataset (~470 requests, a couple of minutes), exits 0, and
   must never modify `data/dog_rules.json`, `data/extra_beaches.json`
   or `data/counties.json` (`git status` after the run should show only
   `data/beaches.json` changed). Expect many `WARN: no dog data for ...` lines — correct,
   most of England outside Kent has no curated dog-rule entry yet.

Gotcha: `.filter-group { display:flex }` needs the `[hidden]` CSS
override in styles.css — regressions show the Month select while
Dogs ≠ "Friendly in month…".
