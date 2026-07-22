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
   - Search a beach that's still uncurated (e.g. "west wittering" or
     "firestone bay") → grey "Dog rules unknown" badge — expected for
     167 of the 470 beaches. 303 beaches are curated (136 friendly,
     165 seasonal, 2 banned); "spittal" and "blackpool" are curated
     now too (North East/North West were swept), so don't use them as
     unknown-badge examples — re-check `data/beaches.json` for a
     current `status: "unknown"` example if these drift.
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
   `data/beaches.json` changed). Expect ~167 `WARN: no dog data for ...`
   lines — correct, those beaches have no curated dog-rule entry yet
   (see PRODUCTION_PLAN.md's Expand coverage list for which counties).
7. Launch-hygiene checks (Phase 0):
   - Favicon: browser tab shows the paw-print icon (`favicon.svg`).
   - Open the devtools console before and after loading the page —
     zero errors, and specifically zero Content-Security-Policy
     violation messages (map tiles, Leaflet CSS/JS from unpkg, and the
     app's own script/style must all load clean under the CSP meta tag
     in `index.html`).
   - Footer shows two human-readable dates ("Dataset generated 22 July
     2026 · 470 beaches" and "Dog rules last verified <oldest
     `accessed` date>"), not raw ISO strings, plus a working "Dog
     rules wrong? Report it" link.
   - `http://localhost:8741/404.html` renders the same header/footer
     visual language as the main page and a link back home.
   - Kill the server (or rename `data/beaches.json` temporarily) and
     reload: the list shows a plain, non-technical error message, with
     the `python3 -m http.server` dev hint appearing only because
     `localhost` is the hostname — check `err` details land in the
     console instead of the visible message.

Gotcha: `.filter-group { display:flex }` needs the `[hidden]` CSS
override in styles.css — regressions show the Month select while
Dogs ≠ "Friendly in month…".
