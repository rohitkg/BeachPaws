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
   - Region "Any" lists every distinct `region` value in the dataset
     (EA regionalOrganization areas, e.g. South East, South West, North
     West, North East, Anglian, Midlands). Selecting one filters both
     the list and the map and updates the result count to only beaches
     in that region.
   - Search a Kent beach name (e.g. "margate" or "margaret's" — the
     latter checks backtick-normalization against the EA's "St
     Margaret`s Bay") → still finds the curated Kent entry with its
     colored dog badge (green/amber/red) and a working source link.
   - Search a non-Kent beach (e.g. "spittal" or "blackpool") → grey
     "Dog rules unknown" badge — expected for the ~434 beaches outside
     the currently-curated Kent set.
   - Water monitoring "Not monitored" → 6 (the curated extras, all
     Thanet); "EA-monitored" → the rest. "?" button toggles the
     designation explainer (works pre-data-load; listener bound
     outside initControls).
   - Reset filters button → all controls (including Region) back to
     Any/empty, full count shown.
5. "Get directions" on a card: opens a new tab to
   `google.com/maps/dir/?api=1&destination=<lat>,<lng>` for a beach
   with coordinates, or the `google.com/maps/search/...` fallback for
   a coords-null beach (e.g. Sandgate Granville Parade). Clicking it
   must **not** pan the map (the card's click handler bails on
   `ev.target.tagName === "A"`); clicking elsewhere on the card still
   pans the map and opens the marker popup.
6. Data refresh: `python3 scripts/build_data.py` — pages the whole EA
   England dataset (~470 requests, a couple of minutes), exits 0, and
   must never modify `data/dog_rules.json` or `data/extra_beaches.json`
   (`git status` after the run should show only `data/beaches.json`
   changed). Expect many `WARN: no dog data for ...` lines — correct,
   most of England outside Kent has no curated dog-rule entry yet.

Gotcha: `.filter-group { display:flex }` needs the `[hidden]` CSS
override in styles.css — regressions show the Month select while
Dogs ≠ "Friendly in month…".
