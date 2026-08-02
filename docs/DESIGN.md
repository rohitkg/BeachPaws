# BeachPaws design system

The visual language for the BeachPaws front end. Every value here exists as a
CSS custom property in `styles.css` (`:root` block). Change tokens there, not
in component rules. `app.js` duplicates the four dog-status colors in
`STATUS_COLORS` (Leaflet markers can't read CSS variables per-marker cheaply);
if you change a status token, change both places.

## Direction

BeachPaws is a utility: a dog owner on a phone checking beach rules before
travelling. The design serves two ideas:

1. **Dog status is the primary datum.** Each beach card carries a 4px left
   "status spine" in its dog-status color, the same hue as its map marker, so
   the list and map read as one system at a glance.
2. **Provenance is the differentiator.** Hand-curated, dated, sourced dog
   rules are what makes the site trustworthy, so all provenance metadata
   (checked dates, dataset line, result count) is set in monospace, styled as
   a record rather than prose.

One decorative flourish: the "tide line", a 4px sea-to-sand gradient under the
header. Everything else stays quiet.

## Tokens

### Color

| Token | Value | Use |
|---|---|---|
| `--c-mist` | `#edf3f5` | Page background |
| `--c-foam` | `#ffffff` | Cards, controls, popups |
| `--c-ink` | `#16303c` | Primary text |
| `--c-slate` | `#4a626f` | Secondary text, labels |
| `--c-faint` | `#5c707e` | Provenance / fine print (must stay ≥4.5:1 on foam and mist; it sets 0.75rem text) |
| `--c-line` | `#d5e0e4` | Borders |
| `--c-line-strong` | `#a9bcc4` | Hover borders |
| `--c-sea` | `#0f6e8c` | Links, focus rings, accents |
| `--c-sea-deep` | `#0b516b` | Dark accent (Good water badge) |
| `--c-sand` | `#c9a24b` | Tide-line end |
| `--c-friendly` | `#1e7a46` | Status: friendly (spine + marker + green badges) |
| `--c-seasonal` | `#b25e0b` | Status: seasonal |
| `--c-banned` | `#b02a21` | Status: banned (+ red badges) |
| `--c-unknown` | `#5c6b76` | Status: unknown |

Badge backgrounds are fixed light tints (`#ddf1e4`, `#fbead3`, `#f9dedb`,
`#f5ead2`, `#e7eef1`, `#e7ebed`, `#dbecf6`) paired with the tokens above for
text; all pairs clear WCAG AA at badge sizes.

### Type

| Token | Value | Use |
|---|---|---|
| `--font-ui` | system humanist stack | Everything except provenance |
| `--font-data` | `ui-monospace` stack | Checked dates, dataset meta, result count |
| `--text-display` | 1.7rem / 800 / -0.02em | `h1` (1.45rem on phone) |
| `--text-title` | 1.05rem / 700 | Beach card names |
| `--text-body` | 0.95rem | Body, controls (1rem on phone, stops iOS focus zoom) |
| `--text-small` | 0.85rem | Notes, footer |
| `--text-micro` | 0.75rem | Badges, labels, provenance |

Filter labels are micro-size, 700 weight, uppercase, +0.05em: the "eyebrow"
treatment. Scoped to `.filter-group > label` only: multiselect option rows are
also `<label>`s and must stay normal case.

### Space, shape, elevation

- Spacing: 4px scale, `--s-1` (0.25rem) … `--s-6` (2rem).
- Radii: `--r-control` 8px (inputs, buttons), `--r-card` 12px (cards, map),
  `--r-pill` 999px (badges, region tag).
- Shadows: `--shadow-card` (resting card), `--shadow-pop` (open popups, card
  hover).
- Motion: card hover transitions 0.15s ease; disabled under
  `prefers-reduced-motion`.

## Components

### Beach card
`article.beach-card.dog-<status>`: the status class drives the spine color.
Hover: stronger border + `--shadow-pop` lift. The whole card is clickable
(pans the map); inner links keep their own behavior.

### Badge
`.badge` pill + one variant class (`badge-sand/-neutral/-green/-amber/-red/
-grey/-wq-<Class>`). Micro type, 600 weight, no wrapping.

### Multiselect (Sand / County / Council)
Summary button + absolute popup panel (search input optional, scrollable
checkbox list). Panel z-index 1101, above the sticky filter bar. On phones
the button goes full width and the panel pins `left:0; right:0`.

### Map legend
`.map-legend`, a Leaflet `bottomleft` control built in `initMap` (`app.js`).
Decodes the four marker colors with a labeled dot each ("Dogs welcome" /
"Seasonal rules" / "No dogs" / "Unknown"), so the map's color coding is
explained in place and never color-only. Labels must track `dogs.status`
values; dot colors come from `.legend-dot.dog-<status>` rules.

### Filter bar
Sticky `fieldset.filters`, z-index 1100, must beat Leaflet's controls
(z-index 1000), which compete globally once `#map` is `position: static` on
small screens. Desktop/tablet: label-over-control groups in a flex wrap
(`.filter-controls` is `display: contents`). Phone (≤700px): only Search and
the Filters button stay visible; the button toggles `body.filters-open`,
showing a single-column panel (own scroll at `max-height: calc(100vh - 140px)`).
The button reads "Filters · n" when n filter groups are active, so a collapsed
panel can't silently hide an applied filter (search excluded; it stays
visible).

## Layout / breakpoints

| Range | Layout |
|---|---|
| ≥900px | Two columns: scrollable card list + sticky map (`top: 90px`) |
| 700–899px | Single column, map first at 50vh, filters still a wrap row |
| ≤700px | Map 42vh, collapsed filters, full-width 44px-min controls, 16px input text |

Gotcha (learned the hard way): Leaflet inlines `position: relative` on a
container whose computed position is `static`, so the stacked breakpoints must
reset `top: auto` or the base rule's sticky `top: 90px` re-applies as a
relative offset and the map overlaps the list.

## Accessibility floor

- `:focus-visible`: 2px `--c-sea` outline, 2px offset, everywhere.
- Phone touch targets: 44px min height on all controls, 40px option rows.
- Filters toggle and multiselect buttons carry `aria-expanded`; result count
  is `aria-live`; filters are a `fieldset` with a visually-hidden legend.
- Status is never color-only: every spine color is restated by a text badge.
