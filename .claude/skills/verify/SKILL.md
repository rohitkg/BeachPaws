---
name: verify
description: How to run and verify the Kent Beach Filter site end-to-end.
---

# Verify Kent Beach Filter

No build step. Surface = browser GUI.

1. Serve: `python3 -m http.server 8741` from repo root (fetch of
   `data/beaches.json` fails on `file://`).
2. Open `http://localhost:8741` in the browser (claude-in-chrome works).
3. Drive the filters and check counts against the dataset (30 EA
   bathing waters + 6 curated extras in `data/extra_beaches.json`,
   which carry a grey "Not an EA bathing water" badge):
   - Dogs "Friendly year round" → 13 of 36
   - Sand "Sandy" + "Friendly year round" → 12 (incl. Kingsgate Bay,
     Dumpton Gap)
   - Dogs "Friendly in month…": April/October → 36, May–Sep → 20
     (13 friendly + 7 amber "restricted hours" beaches)
   - Dogs "Not allowed" → 0, empty state, markers cleared
   - Water monitoring "Not monitored" → 6 (the curated extras);
     "EA-monitored" → 30. "?" button toggles the designation explainer
     (works pre-data-load; listener bound outside initControls)
   - Sand "Not sandy" → 3 (Sandgate excluded: no EA sediment data,
     appears only under "Any" with grey "Sediment unknown" badge)
4. Click a list card → map pans + popup opens with same badges.
5. Data refresh: `python3 scripts/build_data.py` — ~35 EA API calls,
   exits 0, must never modify `data/dog_rules.json`. Expected warnings:
   Sandgate (ukj4208-13350) has no sediment/water-quality in EA data.

Gotcha: `.filter-group { display:flex }` needs the `[hidden]` CSS
override in styles.css — regressions show the Month select while
Dogs ≠ "Friendly in month…".
