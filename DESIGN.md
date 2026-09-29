# Thrive Causemetics Dashboard Design Standard

> **What this is:** the one visual standard for every Thrive Causemetics internal dashboard.
> Drop this file into a dashboard repo (as `DESIGN.md`) and tell Claude: *"Restyle this
> dashboard to follow DESIGN.md. Visual changes only."*
>
> **Source:** built from the Launch Dashboard (base palette, header, cards, KPI tiles) and
> Product 360 (gold accent, solid table headers, alert boxes, brand mark).
>
> **Status:** v1, light mode only. The palette is for internal tools and hasn't been through
> Brand review.

---

## 0. The Golden Rule: Visual Only

This standard changes **how things look**. It never changes **what is there or where it sits**.

| ✅ Change | ❌ Never change |
|---|---|
| Colors, gradients, backgrounds | Page layout, grid structure, column counts |
| Font family, sizes, weights | Which filters exist, their order, their behavior |
| Border radius, borders, shadows | Which charts exist, chart types, what they plot |
| Padding *inside* components | Table columns, column order, sorting logic |
| Tab / button / badge styling | Tabs (which ones, their order, their labels) |
| Chart colors, gridlines, fonts | Data, calculations, metric definitions, copy/labels |
| KPI tile styling | Number of KPI tiles, what they measure |

Rules for whoever applies this (person or Claude):

1. **Map values onto existing selectors.** Don't rename classes or restructure HTML to fit the
   class names in this file. They're examples. If the dashboard calls it `.metric-box`, restyle
   `.metric-box`.
2. **Don't add or remove elements.** One exception: adding the brand mark to the header is
   optional (§3.1).
3. **Keep meaning-colors meaningful.** If a dashboard already uses red for "bad" or green for
   "good", keep that and use the status tokens (§1.3).
4. **When unsure, leave it alone** and list it in the PR description.
5. **Test before you ship.** Screenshot every tab before and after. Every filter, chart and table
   should work exactly as before.

---

## 1. Color Tokens

Paste this `:root` block at the top of the dashboard's stylesheet. Use `var(--token)` everywhere
instead of raw hex values.

```css
:root {
  /* Brand */
  --tc-teal:        #3A9E98;  /* primary: active tabs, buttons, links, main series */
  --tc-teal-dark:   #1F6E6A;  /* hover, table headers, section headings */
  --tc-teal-light:  #E6F4F3;  /* row hover, totals, soft highlights, chips */
  --tc-navy:        #1C2B3A;  /* header gradient start, body text, 3rd series */
  --tc-gold:        #C9A84C;  /* accent: brand mark, 2nd series, highlights */
  --tc-gold-soft:   #F3E7C3;  /* gold backgrounds (notices, hint dots) */

  /* Surfaces & text */
  --bg:             #F0F2F5;  /* page background */
  --surface:        #FFFFFF;  /* cards, tiles, filter bar, tables */
  --surface-2:      #F7F9FB;  /* zebra rows, sub-headers, inset panels */
  --text:           #1C2B3A;  /* body text */
  --muted:          #6B7A8D;  /* labels, captions, secondary text */
  --border:         #E2E8EF;  /* card borders, dividers, chart gridlines */
  --border-strong:  #CBD5E1;  /* input borders */

  /* Status (meaning only, never decoration) */
  --positive:       #22A06B;  /* up, on track, good */
  --warn:           #F59E0B;  /* watch, at risk */
  --danger:         #EF4444;  /* down, critical, off track */
  --info:           #0EA5E9;

  /* Shape */
  --r:              12px;     /* cards, tiles, panels */
  --r-sm:           8px;      /* buttons, inputs, dropdowns */
  --r-pill:         999px;    /* chips, badges, pills */
  --shadow-sm:      0 1px 3px rgba(28,43,58,.07);
  --shadow-md:      0 4px 20px rgba(28,43,58,.10);
  --shadow-pop:     0 8px 24px rgba(28,43,58,.16);  /* dropdown panels */
}
```

### 1.1 Palette at a glance

| Swatch | Token | Hex | Use for |
|---|---|---|---|
| 🟢 | `--tc-teal` | `#3A9E98` | Primary everything |
| 🌲 | `--tc-teal-dark` | `#1F6E6A` | Hover, table header background, headings |
| 🫧 | `--tc-teal-light` | `#E6F4F3` | Hover rows, totals rows, active chips |
| 🌑 | `--tc-navy` | `#1C2B3A` | Header, text |
| 🟡 | `--tc-gold` | `#C9A84C` | Accent, second series |
| ⬜ | `--bg` | `#F0F2F5` | Page background |
| ▫️ | `--border` | `#E2E8EF` | Lines and gridlines |

### 1.2 Tinted text on tinted backgrounds

When text sits on a colored background, use the darker ink from this table. Don't use the base
color, because it fails contrast.

| Tone | Background | Border | Text |
|---|---|---|---|
| Good | `rgba(34,160,107,.10)` / `#EDF8F1` | `#BFE3CC` | `#166534` |
| Watch | `rgba(245,158,11,.10)` / `#FDF6E3` | `#F3E7C3` | `#92400E` |
| Critical | `rgba(239,68,68,.10)` / `#FDEFEC` | `#EEC4BB` | `#991B1B` |
| Brand | `var(--tc-teal-light)` | `var(--tc-teal)` | `var(--tc-teal-dark)` |
| Gold | `rgba(201,168,76,.12)` | `rgba(201,168,76,.4)` | `#7A5C00` |
| Neutral | `rgba(107,122,141,.10)` | `var(--border)` | `var(--muted)` |

### 1.3 Status colors (these mean something)

- **Up / positive delta / on plan (≥100%)** → `--positive`
- **Watch / 85–99% of plan / tight stock** → `--warn`
- **Down / negative delta / <85% of plan / critical** → `--danger`
- **No data / unknown** → `#9CA3AF`

If a dashboard already has its own thresholds, **keep the thresholds** and only swap the colors.

---

## 2. Typography

```css
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  color: var(--text);
  background: var(--bg);
  -webkit-font-smoothing: antialiased;
}
td.r, .kpi-value, .num { font-variant-numeric: tabular-nums; }  /* numbers line up */
```

| Element | Size | Weight | Color | Extras |
|---|---|---|---|---|
| Header title (h1) | 21–22px | 700 | `#fff` | `letter-spacing: .3px` |
| Header subtitle | 12–13px | 400 | `#fff` at `opacity: .7` | |
| Card / chart title | 13–15px | 600 | `--text` (or `--tc-teal-dark`) | |
| Card subtitle / description | 11–12px | 400 | `--muted` | |
| Section label (above a group) | 10–11px | 700 | `--muted` | UPPERCASE, `letter-spacing: 1.2px`, 1px bottom border |
| KPI label | 10–11px | 700 | `--muted` | UPPERCASE, `letter-spacing: .8px` |
| KPI value | 23–24px | 700 | `--text` | `line-height: 1`, tabular nums |
| KPI delta / sub | 11–12px | 600 | status color / `--muted` | |
| Table body | 12.5–13px | 400 | `--text` | |
| Table header | 10.5–11px | 600 | `#fff` | UPPERCASE, `letter-spacing: .5px` |
| Filter label | 10–10.5px | 700 | `--muted` | UPPERCASE, `letter-spacing: .7px` |
| Notes / footnotes | 11px | 400 | `--muted` | `line-height: 1.55` |
| Code / SQL / IDs | 11.5–12px | 400 | `--text` | `ui-monospace, SFMono-Regular, Menlo, monospace` on `--surface-2` |

Don't load web fonts. The system stack is fast and consistent in the portal iframe.

---

## 3. Components

The snippets below are **reference styling**. Apply the values to whatever the dashboard already has.

### 3.1 Header (the brand signature)

The header is how people recognize a dashboard as "one of ours". Every dashboard gets the same one.

```css
.hdr {
  background: linear-gradient(135deg, var(--tc-navy) 0%, var(--tc-teal-dark) 100%);
  color: #fff;
  padding: 18px 36px 14px;         /* keep the dashboard's existing padding if it differs */
}
.hdr h1   { font-size: 21px; font-weight: 700; letter-spacing: .3px; line-height: 1.25; }
.hdr .sub { font-size: 12px; opacity: .7; margin-top: 3px; }

/* Optional brand mark. The only element this standard allows you to ADD. */
.brand-mark {
  width: 42px; height: 42px; border-radius: 50%; flex: none;
  background: var(--tc-gold); color: var(--tc-navy);
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 17px; letter-spacing: .5px;
  box-shadow: inset 0 0 0 2px rgba(255,255,255,.55);
}
```

```html
<!-- Brand mark markup, placed to the left of the existing title -->
<div class="brand-mark">TC</div>
```

**Subtitle convention:** `Thrive Causemetics · <data source> · refreshed <when>`
e.g. *Thrive Causemetics · refreshed daily from Snowflake · Sep 29, 6:30 AM PT*.
Only reformat an existing subtitle. Don't invent a data source.

**Things that sit on the header** (buttons, dropdowns, stat pills) use frosted white:

```css
.hdr-control, .stat-pill {
  background: rgba(255,255,255,.13);
  border: 1px solid rgba(255,255,255,.25);
  color: #fff; border-radius: var(--r-sm);   /* pills: var(--r-pill) */
  padding: 6px 13px; font-size: 12px; font-weight: 500;
}
.hdr-control:hover { background: rgba(255,255,255,.22); }
.hdr-control option { color: var(--text); }   /* native <select> dropdown text */

/* Colored header pills (optional) */
.stat-pill.good { background: rgba(34,160,107,.28);  border-color: rgba(34,160,107,.45);  color: #8FFFD4; }
.stat-pill.teal { background: rgba(58,158,152,.28);  border-color: rgba(58,158,152,.45);  color: #B0EDEA; }
.stat-pill.gold { background: rgba(201,168,76,.22);  border-color: rgba(201,168,76,.40);  color: #F5DFA4; }
```

### 3.2 Tabs

Restyle tabs **wherever they already are**. Don't move them into or out of the header.

**Tabs on a white bar / on the page (default):**
```css
.tabs-wrap { background: var(--surface); border-bottom: 2px solid var(--border); }
.tab {
  padding: 13px 18px; font-size: 13px; font-weight: 500; color: var(--muted);
  background: none; border: 0; border-bottom: 2px solid transparent; margin-bottom: -2px;
  cursor: pointer; transition: color .15s, border-color .15s; white-space: nowrap;
}
.tab:hover:not(.active) { color: var(--text); }
.tab.active { color: var(--tc-teal-dark); border-bottom-color: var(--tc-teal); font-weight: 600; }
```

**Tabs that live inside the header (e.g. Product 360):**
```css
.hdr .tab        { background: rgba(255,255,255,.09); color: rgba(255,255,255,.85);
                   border-radius: 10px 10px 0 0; border: 0; padding: 11px 18px 13px; font-weight: 600; }
.hdr .tab:hover  { background: rgba(255,255,255,.18); }
.hdr .tab.active { background: var(--bg); color: var(--tc-teal-dark); }
```

### 3.3 Filter bar

Same filters, same order, same behavior. Only the styling changes.

```css
.filterbar {
  background: var(--surface); border-bottom: 1px solid var(--border);   /* or a card: border + var(--r) */
  box-shadow: 0 2px 6px rgba(28,43,58,.05);
  padding: 10px 22px;
}
.filterbar label {
  font-size: 10.5px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .7px; color: var(--muted);
}
select, input[type="text"], input[type="search"], input[type="date"], .ms-toggle {
  border: 1px solid var(--border-strong); border-radius: var(--r-sm);
  background: #fff; color: var(--text); font: inherit; font-size: 13px; padding: 6px 9px;
}
select:focus, input:focus, .ms-toggle:focus {
  outline: none; border-color: var(--tc-teal); box-shadow: 0 0 0 3px rgba(58,158,152,.18);
}

/* Multi-select dropdown panel */
.ms-panel { background: #fff; border: 1px solid var(--border); border-radius: 9px; box-shadow: var(--shadow-pop); }
.ms-option:hover { background: var(--tc-teal-light); }
.ms-toggle .count { background: var(--tc-teal); color: #fff; border-radius: var(--r-pill);
                    font-size: 10.5px; font-weight: 700; padding: 1px 7px; }
input[type="checkbox"], input[type="radio"] { accent-color: var(--tc-teal); }
```

**Preset / chip buttons** (YTD, Last 12 mo, launch toggles, SKU chips):
```css
.chip {
  font-size: 12px; font-weight: 500; padding: 4px 11px; border-radius: var(--r-pill);
  border: 1px solid var(--border); background: #fff; color: var(--muted); cursor: pointer;
}
.chip:hover { border-color: var(--tc-teal); color: var(--tc-teal-dark); }
.chip.on    { background: var(--tc-teal-light); border-color: var(--tc-teal); color: var(--tc-teal-dark); font-weight: 600; }
.chip.off   { background: var(--bg); border-style: dashed; color: var(--muted); }   /* hidden-but-restorable */
```

**Segmented control** (Units / $, WoW / MoM / YoY):
```css
.seg { display: inline-flex; border: 1px solid var(--border); border-radius: var(--r-sm); overflow: hidden; }
.seg button { border: 0; background: #fff; padding: 6px 12px; font-size: 12px; color: var(--muted); cursor: pointer; }
.seg button + button { border-left: 1px solid var(--border); }
.seg button.on { background: var(--tc-teal); color: #fff; font-weight: 600; }
```

### 3.4 Buttons

```css
/* Primary: Export, Apply, Copy, Download */
.btn {
  font: 600 12px inherit; padding: 8px 15px; border: 0; border-radius: var(--r-sm);
  background: var(--tc-teal); color: #fff; cursor: pointer;
  display: inline-flex; align-items: center; gap: 7px; white-space: nowrap;
  box-shadow: 0 1px 3px rgba(28,43,58,.18); transition: background .15s ease;
}
.btn:hover         { background: var(--tc-teal-dark); }
.btn:active        { transform: translateY(1px); }
.btn:focus-visible { outline: 3px solid var(--tc-gold); outline-offset: 2px; }
.btn:disabled      { opacity: .45; cursor: default; }
.btn.sm            { padding: 5px 10px; font-size: 11px; gap: 5px; }

/* Secondary: Reset, Clear, Cancel */
.btn-secondary {
  font: 600 12px inherit; padding: 7px 13px; border-radius: var(--r-sm);
  border: 1px solid var(--border); background: #fff; color: var(--muted); cursor: pointer;
}
.btn-secondary:hover { color: var(--text); border-color: var(--muted); }

/* Text link */
a, .link { color: var(--tc-teal-dark); text-decoration: none; font-weight: 600; }
a:hover, .link:hover { text-decoration: underline; }
```

Export and download buttons are **solid teal**, never ghost. A white button on a white card gets missed.

### 3.5 Cards (charts, panels, guides)

```css
.card {
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--r);
  padding: 18px 20px; box-shadow: var(--shadow-sm);
}
.card-title { font-size: 13.5px; font-weight: 600; color: var(--text); margin-bottom: 4px; }
.card-sub   { font-size: 11.5px; color: var(--muted); margin-bottom: 14px; }

/* Clickable cards only */
.card.clickable { transition: box-shadow .15s, transform .15s; cursor: pointer; }
.card.clickable:hover { box-shadow: var(--shadow-md); transform: translateY(-1px); }

/* Status edge (live / upcoming / archived) */
.card.live     { border-left: 4px solid var(--tc-teal); }
.card.upcoming { border-left: 4px solid var(--border); }
.card.archived { border-left: 4px solid var(--tc-navy); }

/* Section label that sits above a group of cards */
.section-title {
  font-size: 10.5px; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase;
  color: var(--muted); padding-bottom: 8px; margin-bottom: 14px; border-bottom: 1px solid var(--border);
}
```

Keep the existing grid gaps, card counts and column spans. Only the card's own look changes.

### 3.6 KPI tiles

A **3px colored stripe on top** is the house style.

```css
.kpi {
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--r);
  padding: 16px 20px; position: relative; overflow: hidden;
}
.kpi::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: var(--tc-teal); }
.kpi.gold::before  { background: var(--tc-gold); }
.kpi.navy::before  { background: var(--tc-navy); }
.kpi.green::before { background: var(--positive); }
.kpi.warn::before  { background: var(--warn); }

.kpi-label { font-size: 10px; font-weight: 700; letter-spacing: .9px; text-transform: uppercase; color: var(--muted); margin-bottom: 6px; }
.kpi-value { font-size: 24px; font-weight: 700; line-height: 1; color: var(--text); font-variant-numeric: tabular-nums; }
.kpi-sub   { font-size: 11px; color: var(--muted); margin-top: 5px; }
.kpi-delta { font-size: 11.5px; font-weight: 600; margin-top: 5px; }
.kpi-delta.pos { color: var(--positive); }
.kpi-delta.neg { color: var(--danger); }
.kpi-delta .vs { color: var(--muted); font-weight: 500; }

/* Progress bar under a KPI (% to plan) */
.kpi-bar      { height: 4px; background: var(--border); border-radius: 2px; margin-top: 8px; overflow: hidden; }
.kpi-bar-fill { height: 100%; border-radius: 2px; }   /* color = status color by threshold */
```

**Stripe color order** for a row of tiles: teal → gold → navy → green → then repeat. If a
tile's stripe already carries meaning (e.g. red for at-risk), keep it.

### 3.7 Tables

Solid dark-teal header, zebra rows, teal hover, totals row in soft teal.

```css
.table-wrap { overflow-x: auto; border-radius: var(--r); }   /* horizontal scroll stays as-is */
table { width: 100%; border-collapse: collapse; font-size: 12.8px; }

thead th {
  background: var(--tc-teal-dark); color: #fff;
  font-size: 10.5px; font-weight: 600; letter-spacing: .5px; text-transform: uppercase;
  padding: 9px 12px; text-align: left; white-space: nowrap;
  position: sticky; top: 0;                       /* only if the table already scrolls */
}
thead th.group { background: var(--tc-navy); text-align: center; }   /* grouped super-headers */
thead th .th-sub { display: block; font-weight: 500; font-size: 9.5px; text-transform: none;
                   letter-spacing: 0; opacity: .75; margin-top: 1px; }

td { padding: 8px 12px; border-bottom: 1px solid var(--border); white-space: nowrap; }
th.r, td.r { text-align: right; font-variant-numeric: tabular-nums; }

tbody tr:nth-child(even) { background: var(--surface-2); }
tbody tr:hover           { background: var(--tc-teal-light); }
tbody tr.clickable       { cursor: pointer; }
tbody tr.selected        { background: #CDEAE7; }

/* Subtotal and total rows */
tr.subtotal td { background: var(--surface-2); font-weight: 600; border-top: 1px solid var(--border); }
tr.total td, tfoot td { background: var(--tc-teal-light); font-weight: 700; border-top: 2px solid var(--tc-teal); }

/* Values */
td .pos, td.pos { color: var(--positive); font-weight: 600; }
td .neg, td.neg { color: var(--danger);   font-weight: 600; }
td.ref          { color: var(--muted); }                       /* reference-only columns */

/* In-cell data bar */
.bar-cell { position: relative; }
.bar-cell .bar { position: absolute; inset: 3px auto 3px 0; background: rgba(58,158,152,.20); border-radius: 3px; }
.bar-cell span { position: relative; }

/* Sort arrows */
th.sorted-asc::after  { content: " ▲"; font-size: 8px; }
th.sorted-desc::after { content: " ▼"; font-size: 8px; }
```

**Heatmap cells:** scale `rgba(58,158,152, α)` with α from `.08` to `.85`. Switch the text to
`#fff` once α > `.45`.

### 3.8 Badges, tags, pills

```css
.badge {                                           /* status of a thing: LIVE, UPCOMING */
  display: inline-block; font-size: 10px; font-weight: 700; letter-spacing: .6px;
  text-transform: uppercase; padding: 3px 10px; border-radius: var(--r-pill); border: 1px solid;
}
.badge.good    { background: rgba(34,160,107,.12);  color: #15794E; border-color: rgba(34,160,107,.3); }
.badge.warn    { background: rgba(245,158,11,.12);  color: #B45309; border-color: rgba(245,158,11,.3); }
.badge.bad     { background: rgba(239,68,68,.12);   color: #991B1B; border-color: rgba(239,68,68,.3); }
.badge.neutral { background: rgba(107,122,141,.10); color: var(--muted); border-color: var(--border); }
.badge.brand   { background: var(--tc-teal-light);  color: var(--tc-teal-dark); border-color: rgba(58,158,152,.35); }

.tag {                                             /* inline in a table cell */
  display: inline-block; font-size: 11px; font-weight: 600; padding: 1px 7px; border-radius: 4px;
}
.tag.good { background: rgba(34,160,107,.10); color: #166534; }
.tag.warn { background: rgba(245,158,11,.10); color: #92400E; }
.tag.bad  { background: rgba(239,68,68,.10);  color: #991B1B; }

.kpi-chip { background: var(--tc-teal-light); color: var(--tc-teal-dark);
            border-radius: var(--r-sm); padding: 6px 12px; font-size: 12px; font-weight: 600; }
.kpi-chip.gold { background: rgba(201,168,76,.12); color: #7A5C00; }
```

### 3.9 Alerts, notices, signal cards

```css
.alert { display: block; padding: 10px 14px; border-radius: 9px; border: 1px solid; font-size: 13px; line-height: 1.5; }
.alert.crit  { background: #FDEFEC; border-color: #EEC4BB; color: #7C2D1D; }
.alert.warn  { background: #FDF6E3; border-color: #F3E7C3; color: #6B5316; }
.alert.good  { background: #EDF8F1; border-color: #BFE3CC; color: #1F5C3A; }
.alert.info  { background: var(--tc-teal-light); border-color: rgba(58,158,152,.35); color: var(--tc-teal-dark); }

/* Left-edge signal card ("Needs attention" / "What's working") */
.signal { background: var(--surface); border-radius: var(--r); padding: 14px 18px; border-left: 4px solid var(--muted); }
.signal.attention { border-left-color: var(--danger);   background: #FEF4F4; }
.signal.working   { border-left-color: var(--positive); background: #F1FAF6; }

/* Data-freshness / caveat notice at the top of a page */
.notice { background: #FDF6E3; border: 1px solid var(--tc-gold-soft); color: #6B5316;
          border-radius: var(--r-sm); padding: 8px 14px; font-size: 12.5px; }

/* Error banner */
.error-banner { background: #FEF2F2; border: 1px solid #FECACA; color: #B91C1C;
                border-radius: var(--r); padding: 14px 18px; font-size: 13px; }

/* Little "?" hint dot next to a title */
.hint { display: inline-flex; width: 15px; height: 15px; border-radius: 50%;
        background: var(--tc-gold-soft); color: var(--tc-teal-dark); font-size: 10.5px; font-weight: 800;
        align-items: center; justify-content: center; cursor: help; vertical-align: 2px; }
```

### 3.10 Loading, empty, footer

```css
.loading-overlay { position: fixed; inset: 0; background: rgba(240,242,245,.92); z-index: 200;
                   display: flex; align-items: center; justify-content: center; gap: 12px;
                   font-size: 14px; font-weight: 600; color: var(--tc-teal-dark); }
.spinner { width: 28px; height: 28px; border-radius: 50%;
           border: 3px solid var(--border); border-top-color: var(--tc-teal);
           animation: spin .7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.skeleton { background: var(--border); border-radius: 6px; animation: fade 1.5s ease-in-out infinite; }
@keyframes fade { 0%,100% { opacity: 1 } 50% { opacity: .45 } }

.empty { padding: 28px; text-align: center; font-size: 12.5px; color: var(--muted); }

.footer { text-align: center; padding: 20px 24px; font-size: 11px; color: var(--muted); border-top: 1px solid var(--border); }
.footer a { color: var(--tc-teal-dark); }
```

**Footer convention:** `Thrive Causemetics <Dashboard Name> — Data: <source> · <repo link>`.
Reformat an existing footer only.

---

## 4. Charts

Every chart uses the same palette in the same order, so a color means the same thing everywhere.

### 4.1 Series palette (categorical, use in this order)

```js
const TC_SERIES = [
  '#3A9E98', // 1 teal
  '#C9A84C', // 2 gold
  '#1C2B3A', // 3 navy
  '#22A06B', // 4 green
  '#8B5CF6', // 5 purple
  '#0EA5E9', // 6 sky
  '#8FD3CE', // 7 light teal
  '#6366F1', // 8 indigo
  '#E0A48B', // 9 terracotta
  '#6B7A8D', // 10 slate
];
const tcColor = i => TC_SERIES[i % TC_SERIES.length];
```

Red and amber are **not** in the series palette on purpose. They mean "bad" and "watch".

### 4.2 Fixed meanings (always the same color)

| Series | Color | Style |
|---|---|---|
| **New customers** | `#3A9E98` teal | solid |
| **Returning customers** | `#C9A84C` gold | solid |
| **Actual** (units, sales) | `#3A9E98` teal (or gold for cumulative) | solid line, area fill at `.12` alpha |
| **Plan / forecast / target** | `#6B7A8D` slate | **dashed** `[6, 4]`, no points |
| **Prior year / comparison** | `#8FD3CE` light teal or `#CBD5E1` | thinner line (1.5px) |
| **Spend / secondary bars behind a line** | `#D5DEE6` | bars, `order: 2` |
| **New to category** | `#22A06B` green | |
| **Existing category** | `#3A9E98` teal | |
| **Good / bad in a single-series bar** | `--positive` / `--danger` | |

Leave colors that dashboards pull from data (e.g. a real shade hex per variant) alone. Use
`#3A9E98` as their fallback.

### 4.3 Chart.js defaults

Put this **once**, before any chart is created:

```js
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
Chart.defaults.font.size = 11;
Chart.defaults.color = '#6B7A8D';                                  // axis labels, legend text
Chart.defaults.borderColor = '#E2E8EF';                            // gridlines
Chart.defaults.plugins.legend.labels.boxWidth = 12;
Chart.defaults.plugins.legend.labels.boxHeight = 12;
Chart.defaults.plugins.tooltip.backgroundColor = '#1C2B3A';
Chart.defaults.plugins.tooltip.titleColor = '#FFFFFF';
Chart.defaults.plugins.tooltip.bodyColor = '#E6F4F3';
Chart.defaults.plugins.tooltip.padding = 10;
Chart.defaults.plugins.tooltip.cornerRadius = 8;
Chart.defaults.elements.bar.borderRadius = 4;
Chart.defaults.elements.line.tension = 0.25;
Chart.defaults.elements.line.borderWidth = 2;
Chart.defaults.elements.point.radius = 0;          // show points only on short monthly series (radius 2–3)
Chart.defaults.elements.point.hoverRadius = 4;
Chart.defaults.elements.arc.borderWidth = 2;
Chart.defaults.elements.arc.borderColor = '#FFFFFF';
```

Per-chart conventions:
- **Hide x-axis gridlines** (`grid: { display: false }`) and keep light y gridlines `#E2E8EF`.
  On horizontal bars, do the reverse.
- **Money ticks:** `$12k`, `$1.2M`. **Unit ticks:** `12,345`. **Percent ticks:** `42%`.
- **Donuts:** `borderWidth: 0` or `2` white, `hoverOffset: 6`.
- **Legend:** top, small boxes. The dashboard's existing position wins.
- **Chart height:** keep the existing height. This standard doesn't resize charts.

### 4.4 Not Chart.js?

Apply the same hex values, font stack, gridline color and tooltip colors.

- **Plotly (Python/JS):** `colorway=TC_SERIES`, `font_family` = system stack, `font_color='#6B7A8D'`,
  `plot_bgcolor='#FFFFFF'`, `paper_bgcolor='rgba(0,0,0,0)'`, `gridcolor='#E2E8EF'`,
  `hoverlabel=dict(bgcolor='#1C2B3A', font_color='#FFFFFF')`.
- **Recharts / React:** pass `TC_SERIES[i]` to `fill`/`stroke`, `<CartesianGrid stroke="#E2E8EF" vertical={false} />`,
  axis `tick={{ fill: '#6B7A8D', fontSize: 11 }}`.
- **Streamlit:** set `.streamlit/config.toml`:
  ```toml
  [theme]
  base = "light"
  primaryColor = "#3A9E98"
  backgroundColor = "#F0F2F5"
  secondaryBackgroundColor = "#FFFFFF"
  textColor = "#1C2B3A"
  font = "sans serif"
  ```
- **Matplotlib-rendered images:** `plt.rcParams['axes.prop_cycle'] = cycler(color=TC_SERIES)`,
  gridlines `#E2E8EF`, spines off on top/right.

---

## 5. Spacing & Shape Cheat Sheet

| Thing | Value |
|---|---|
| Card / tile radius | `12px` |
| Button / input radius | `8px` |
| Chip / badge radius | `999px` |
| Tag (in-table) radius | `4px` |
| Card padding | `16–20px` |
| KPI tile padding | `16px 20px` |
| Table cell padding | `8px 12px` |
| Borders | `1px solid #E2E8EF` everywhere |
| Accent edges | KPI top stripe `3px`, card left edge `4px`, totals top rule `2px` |
| Shadows | Resting `--shadow-sm`, hover `--shadow-md`, dropdowns `--shadow-pop`. Nothing heavier. |
| Transitions | `.15s` on hover color, shadow, background |

**Don't change** grid gaps, max-widths, breakpoints or column counts. Those are layout.

---

## 6. Icons & Emoji

- Tab and section emoji already in use (📖 Guide, ⭐ Summary, 🎁 Gifting) **stay as they are**.
  Don't add or remove them.
- Inline SVG icons: `stroke="currentColor"`, `stroke-width="2"` to `2.5`, 13–16px, rounded caps and joins.
- Favicon (optional, if the dashboard has none): a simple emoji SVG data-URI, as in Product 360.

---

## 7. Accessibility Floor

- Body text on white must reach at least 4.5:1. `--text` and `--muted` both pass on `#fff` and `#F0F2F5`.
- **Never put white text on `--tc-gold` or `--warn`.** Use `--tc-navy` text instead.
- Status must never be color-only. Keep the `+`/`−` sign, arrow, label or icon that's already there.
- Keep a visible focus ring: `outline: 3px solid var(--tc-gold)` or the teal glow in §3.3.

---

## 8. Applying This to a Dashboard: Checklist

Work through this in order and tick each item in the PR description.

- [ ] Take **before** screenshots of every tab/view.
- [ ] Add the `:root` token block (§1). Replace hard-coded hex values with tokens.
- [ ] Switch the font stack (§2). Remove any web-font `<link>`.
- [ ] Header: navy→teal gradient, white title, 70% subtitle, frosted controls (§3.1). Brand mark optional.
- [ ] Tabs restyled in place (§3.2).
- [ ] Filter bar: labels, inputs, focus ring, chips, dropdowns (§3.3). **Same filters, same order.**
- [ ] Buttons (§3.4) and cards (§3.5).
- [ ] KPI tiles: top stripe, label/value/delta type (§3.6).
- [ ] Tables: teal-dark header, zebra, hover, totals (§3.7). **Same columns, same order.**
- [ ] Badges, alerts, notices, loading, footer (§3.8–3.10).
- [ ] Charts: defaults + series palette + fixed meanings (§4). **Same charts, same types.**
- [ ] Search for leftover off-palette colors: `grep -oE '#[0-9a-fA-F]{6}' <files> | sort | uniq -c | sort -rn`.
- [ ] Take **after** screenshots. Check that every filter, sort, click-through, export and tab still works.
- [ ] Check it inside the portal iframe at a 13" laptop width (~1280px). There should be no new
      horizontal scroll.
- [ ] If anything was ambiguous and left alone, list it in the PR.

---

## 9. Prompt for Claude Code

Paste this into Claude Code in any dashboard repo that has this file as `DESIGN.md`:

> Restyle this dashboard to follow `DESIGN.md`. **Visual changes only.** Don't change layout,
> grid structure, filters, charts, chart types, tables, columns, tabs, labels, data or
> calculations. Map the design tokens and component styles onto the existing selectors
> instead of renaming classes or restructuring markup. The only element you may add is the
> optional header brand mark. Work through the checklist in §8. Before pushing, run the app and
> confirm every tab, filter, sort and export still works, then list anything you deliberately
> left alone in the PR description.

---

## Appendix: Where Each Choice Came From

| Choice | Source |
|---|---|
| Teal `#3A9E98` / `#1F6E6A` / `#E6F4F3`, navy, gold `#C9A84C` | Launch Dashboard |
| Navy→teal header gradient, frosted header controls, colored header pills | Launch Dashboard |
| Gray page background, system font, 12px radius, KPI top stripe | Launch Dashboard |
| Solid export buttons, segmented controls, chips, signal cards, badges | Launch Dashboard |
| Gold "TC" brand mark, gold soft notices, `?` hint dots | Product 360 |
| Solid dark-teal table headers, zebra rows, totals rule, in-cell bars, heatmap | Product 360 |
| Crit / watch / good alert boxes | Product 360 |
| Multi-select dropdown styling | Product 360 |
| Series palette | Launch order (teal, gold, navy, green, purple, sky), with red/amber removed and Product 360's light teal and terracotta added |
