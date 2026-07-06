# PROJECT.md — Pepeha Mapped (GISC401)

> Paste this at the start of each new Claude Chat session.
> Keep under ~120 lines. Session history in git. Locked decisions in DECISIONS.md.
> Session Log is temporary — collapse into Current State/Backlog at next session open, then clear it.

---

## What This Is

A procedurally generated five-page dark-themed PDF pepeha for GISC401
(University of Canterbury, 2026). All geodata fetched from live web services
at runtime — no bundled files. Marker opens `main.ipynb`, pastes a LINZ API
key, runs all cells, receives a PDF.

**Submission deliverables:**
- `GISC401-MapYourPepeha-2026-Z.Hynd.pdf` — produced by the notebook
- `ZHynd_GISC401-Pepeha.zip` — notebook + requirements + README (no geodata)

---
## Submission Snapshot (2026-05-09)

Submitted state tagged as `assignment-submission-2026-05-09`. Submission file: `ZHynd_GISC401-Pepeha.zip`.

In zip: `main.ipynb`, `README.md`, `requirements.txt`, `environment.yml`, full `src/` tree.

Excluded: `local_resources/` (fetched at runtime), `output/` (generated at runtime), all `__pycache__/`, `.claude/`, `.vscode/`, `.gitignore`, `scratch/` directory, `scratch.ipynb`, `codebase_mid-level_description.txt`, `comment_sweep_report.md`, and the `.ai/` directory.

LINZ API key has never been pasted into `main.ipynb` or any other tracked source file -- only at runtime, copy-pasted from a local scratch notebook. Verify `scratch.ipynb` is actually gitignored, and run a `git log` history scan before flipping the repo public, just to confirm no key ever slipped into a tracked file.

---

## Current State

**Status:** Submitted 2026-05-09. Project is in post-submission limbo pending the public release audit pass. Next session is likely months away. Pre-submission work (commenting and docstring pass across all 14 `src/` files; README rewrite) was completed before submission -- see the Submission Snapshot above and the Session Log below for detail.

**Next action:** None — project complete and published as a portfolio item.

---

## Session Log

> Retained as historical context for whoever picks up the post-submission cleanup, rather than collapsed-and-cleared per the standing rule. Future session should start a fresh date heading and collapse this one into git history at that point.

### 2026-05-09

- README ## Known issues: rewritten with ### Runtime warnings and ### Tech debt subsections. New runtime item: PDF preview (works on the uni's ondemand JupyterLab server, fails locally; workaround is to navigate to /output). Two new tech debt items: LINZ API key via env var, per-map-module fetch composition.
- Both tech debt items fact-checked against codebase_mid-level_description.txt before drafting and reframed. First: the env-var-reading inside linz.py is still load-bearing — the pivot was from "user's shell env var" to "user pastes key, orchestrate sets the var", and the import-ordering constraint in orchestrate.py is the visible artefact. Second: src/data/ does own raw I/O; the coupling is at the per-element fetch-composition level inside src/maps/, with progress-message granularity in orchestrate.py as the cost.
- orchestrate.py inline comment on the IFrame PDF preview corrected: "JupyterHub" → "the uni's ondemand JupyterLab server".
- README refactor pass: hard line wraps removed across all prose sections; em-dashes converted to `--` throughout (including the project-structure ASCII tree, with a one-space alignment fix on the `maps/` continuation line); backticks applied consistently for file/function/path/env-var references (`linz.py`, `orchestrate.py`, `LINZ_API_KEY`, `fetch_*_data()`, `src/`, `src/data/`, `src/maps/`, `layer-51153`, `rasterio`, `GDAL`, `cartopy`, `inferno` first reference only). Two typos fixed inline: "he actual fetching" → "The actual fetching", and missing space after "runs." in the Working with Claude paragraph. "Shapely--GDAL" left as-is and flagged (compound-word style, possible alternatives: single hyphen, slash, or restructure).
- Submission note drafted for Moodle: three sentences covering what's in the zip, what's deliberately excluded, and pointer to README for setup.
- Submission zip contents decided: main.ipynb, README.md, requirements.txt, environment.yml, and the full src/ tree. Excluded: local_resources/, output/, all __pycache__/, .claude/, .vscode/, .gitignore, scratch.ipynb, comment_sweep_report.md, .ai/ directory excluded for submission -- broader framing decision (keep/redact/remove for public release) remains on the Backlog as a post-submission item.
- Two repo-hygiene observations flagged for later: stale __pycache__/config.cpython-311.pyc at project root suggesting a config.py that no longer exists; mixed 3.11/3.12 .pyc files in src/data/__pycache__/ and src/__pycache__/ indicating a different env was used at some point. Both harmless.
- config.cpython-311.pyc deleted from local directory.
- Submitted.

---

## Backlog

> Active todos only. Delete when done -- history in git.
> `[?]` = needs discussion before executing.

**Post submission:**
- [ ] Public release audit complete — repo published as portfolio item.

---

## Standing Rules

- All geospatial operations in NZTM2000 (EPSG:2193) unless stated otherwise
- Inset maps use Natural Earth — never LINZ
- Every public function needs a one-line docstring
- No print statements in `src/data/` or `src/maps/` — `orchestrate.py` exempt
- Type hints on all function signatures
- All colours and sizes from `styles.py` — never hardcode hex strings or colour names in modules
- One file at a time — stop and report after each
- Flag anything that looks wrong rather than silently fixing it
- Never modify `.env`
- Read `.ai/DECISIONS.md` at the start of every CC session before touching any code
- After each completed task: append to Session Log, then report back. Log as you go, not at end of session.
- Git pushes done manually by Zak — CC does not push
- Claude Chat writes CC prompts — CC reads files directly, does not ask Chat to read them
- Scratch-test before editing production files; report results before moving on
- Completed backlog items are deleted, never struck through
- `ast.parse()` syntax checks require `encoding='utf-8'` -- default cp1252 fails on macrons
- "Log that" = append a brief entry to Session Log
- Open: paste PROJECT.md → Chat proposes collapsed update → wait for Zak confirmation → proceed

---

## Reference Context

**Pepeha:**

    Kia ora tātou
    Ko Tapuae-O-Uenuku te maunga
    Ko Wairau te awa
    Ko Rongowhakaata te iwi
    Nō Te Waipounamu ahau
    He akonga ahau ki te Whare Wānanga o Waitaha
    Ko Zak tōku ingoa
    Tēnā tātou katoa

**PDF page structure:**

| Page | Content |
|------|---------|
| 1 | Opening globe (clean) + "Kia ora tātou" |
| 2 | Maunga map + "Ko Tapuae-O-Uenuku te maunga" |
| 3 | Awa map + "Ko Wairau te awa" |
| 4 | Iwi map + "Ko Rongowhakaata te iwi" |
| 5 | Closing globe (annotated) + four pepeha lines + full attribution colophon |

**Key LINZ layer IDs:**
- `layer-51153` — NZ land polygons (EPSG:4167 — always pass `bbox_crs="EPSG:2193"`)
- `layer-103632` — Wairau river lines
- `layer-103631` — Wairau river polygons

**Key file locations:**
- `fetch_globe_data()` — `src/data/globe.py`
- Natural Earth cache — `local_resources/natural_earth/`

**Caching pipeline — four levels, never collapse or bypass:**
1. DEM tiles → `local_resources/dem_tiles/`
2. Vector data → `local_resources/linz/` and `local_resources/gdc/`
3. Rendered PNGs → `output/`
4. PDF → `output/GISC401-MapYourPepeha-2026-Z.Hynd.pdf`