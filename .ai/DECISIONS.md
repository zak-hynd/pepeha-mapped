# DECISIONS.md — Pepeha Mapped (GISC401)

> Read this at the start of every CC session before touching any code.
> Only decisions whose silent reversion would break something or require
> significant debugging time. Not a style guide or changelog.

---

## CRS / Data Sources

- [`linz.py` `fetch_layer()`] layer-51153 is EPSG:4167 — always pass
  `bbox_crs="EPSG:2193"` when querying with NZTM coordinates. Don't make optional.
- [`awa.py`] rivers: LINZ layer-103632 (lines) + layer-103631 (polygons),
  `max_features=50000` — confirmed necessary to avoid truncation. Don't reduce.
- [`globe.py`] Rakiura: loaded from `nz_outline.gpkg` index 19, simplified 5000m —
  absent from NE 110m countries layer. Don't remove.
- [insets] Natural Earth only — never LINZ.

## Rendering / Pipeline

- [`globe.py`] graticules: pyproj Transformer direct, not geopandas `to_crs()`.
  Don't switch.
- [`globe.py`] countries: `dissolve()` before `to_crs()`. Don't skip.
- [`globe.py`] projection: orthographic centred ~-43.5°S, 172.6°E. LAEA abandoned
  (antimeridian artefacts). Don't revert.
- [`iwi.py`] polygon cleaning: overlay-intersect with layer-51153, then dissolve.
  Coastline buffer approach broke. Don't revert.
- [all modules] axis limits: `set_xlim`/`set_ylim` before `add_scalebar`,
  `add_north_arrow`, `add_inset`. Don't reorder.
- [all modules] no `tight_layout()`. Don't re-add.
- [`common.py` `add_inset()`] signature: `(fig, main_ax, main_xlim, main_ylim,
  rect_color)` — anchored with `ax.get_position()`. All three call sites pass
  `rect_color=PALETTE["maunga/awa/iwi"]` respectively. Don't change without
  updating all call sites.

## Notebook / Pipeline

- [`linz.py`] API key: read at call time via `_linz_wfs_url()`, never at import.
- [`orchestrate.py`] entry point: single `run()` function — fetch, render, assemble.
- [`orchestrate.py`] DPI: 250. Don't reduce below 200.
- [caching] four levels — DEM tiles, vector data, rendered PNGs, PDF. Never
  collapse or bypass.
- [PDF] structure: 5 pages, map above text, dark theme throughout.
- [PDF] globe rect (pages 1 and 5): `[0.04, 0.32, 0.92, 0.65]` — square-corrected
  for A4. Don't adjust without checking both pages.
- [`main.ipynb`] API key: `if _key: os.environ[...]` — never unconditional.

## Environment

- [CC / shell] CC cannot activate the conda env from PowerShell — runtime checks
  must be run by Zak. CC can use `ast.parse()` for syntax verification only.
- [CC / shell] `ast.parse()` on files with macrons: requires `encoding='utf-8'` —
  default cp1252 will fail.
- fiona removed from orchestrate.py package check — geopandas 1.0+ uses pyogrio, fiona no longer required

## Documentation

- [docstrings + comments] layered approach: short module docstrings (two-sentence
  what + where in pipeline), plain-language function docstrings for non-obvious
  behaviour, inline block comments for tricky chunks. Source-of-truth check is
  `codebase_mid-level_description.txt` — anything flagged there as "non-obvious
  detail" should be captured at one of the three layers. Don't collapse the
  layers or let the description file drift out of sync with the codebase.