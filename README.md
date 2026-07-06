# Pepeha Mapped

A procedurally generated PDF pepeha, built for GISC401 (Foundations of Geospatial Data Science) as part of a postgraduate programme in Geospatial Data Science at the University of Canterbury, 2026.

All geodata is fetched from live web services at runtime. No data files are bundled. The output is a five-page dark-themed atlas PDF.

---

## Running the project

### 1. Get a LINZ API key

River and coastline data comes from the LINZ Data Service, which requires a free API key.

Register or log in at [data.linz.govt.nz](https://data.linz.govt.nz), then go to your profile → API Keys. Or go directly to [data.linz.govt.nz/my/api](https://data.linz.govt.nz/my/api/).

### 2. Set up the environment

**conda (recommended):**
```bash
conda env create -f environment.yml
conda activate zak-hynd-pepeha-mapped
```

This project was developed on Windows and depends on geospatial packages (`rasterio`, `GDAL`, `cartopy`) that require compiled C libraries. conda handles these cleanly via conda-forge. pip may work on Linux or macOS but is not supported on Windows -- `requirements.txt` is provided as a best-effort fallback only.

**venv (alternative):**

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Windows cmd:        .venv\Scripts\activate.bat
# macOS / Linux:      source .venv/bin/activate
pip install -r requirements.txt
```

On macOS or Linux this generally works -- `pip` provides wheels for `rasterio`, `pyogrio`, and `cartopy` that bundle their C libraries. On Windows, pip-installing the geospatial stack is genuinely fiddly; if you hit compile errors on `GDAL`, `rasterio`, or `cartopy`, fall back to the conda path above.

To remove the venv when done: delete the `.venv/` folder.

### 3. Run

Open `main.ipynb` -- it has setup instructions and two cells to run. Full environment and dependency details are in this README.

On a first run, DEM tiles and vector data are fetched and cached to `local_resources/` -- this takes a few minutes. Subsequent runs are faster.

**Output:** `output/GISC401-MapYourPepeha-2026-Z.Hynd.pdf`

To remove the conda environment when you're done:
```bash
conda env remove -n zak-hynd-pepeha-mapped
```

---

## Data sources

| Data | Source |
|------|--------|
| Elevation (DEM) | Copernicus GLO-90 via AWS S3 COG |
| Rivers (Wairau) | LINZ Data Service WFS (layers 103631, 103632) |
| Land polygons | LINZ Data Service WFS (layer 51153) |
| Iwi rohe (Rongowhakaata) | GDC ArcGIS FeatureServer |
| Coastlines, countries, graticules | Natural Earth |

Main maps: NZTM2000 (EPSG:2193). Globe: orthographic projection centred on Ōtautahi.

---

## About

### The pepeha
```
Kia ora tātou
Ko Tapuae-O-Uenuku te maunga
Ko Wairau te awa
Ko Rongowhakaata te iwi
Nō Te Waipounamu ahau
He akonga ahau ki te Whare Wānanga o Waitaha
Ko Zak tōku ingoa
Tēnā tātou katoa
```

Three landmarks are mapped: Tapuae-O-Uenuku gets a hillshaded DEM, the Wairau a vector river map, Rongowhakaata a rohe polygon. A globe locator -- showing Te Waipounamu and Ōtautahi -- opens and closes the document.

### Design

The visual theme is built around a single colormap -- matplotlib's `inferno` -- sampled at regular intervals to colour each pepeha element. The maunga sits at the warm end (mustard, inferno 0.9), stepping down through deep saffron for the awa (0.75), fiery terracotta for the rohe (0.60), and rosewood for Te Waipounamu (0.50), to a deep purple for Te Whare Wānanga o Waitaha (0.30). The neutral tones -- a muted teal for landmass and off-white platinum for labels and furniture -- came from Coolors.co, chosen to sit alongside the inferno samples without competing with them. All colours and sizes live in `src/maps/styles.py`.

### Why it's built this way

The assignment asked for a mapped pepeha. It didn't ask for a software pipeline. My background is in the geospatial software industry -- previously as a product owner, BA, and tester at companies including Seequent and Landcare Research, and in geomodelling for mining exploration consulting. I'm now doing a postgrad in Geospatial Data Science, partly to formalise skills I've been using in practice for years, and partly to get properly comfortable writing code rather than directing people who write it.

This assignment felt like the right place to explore what end-to-end geospatial data science looks like in Python. Not downloading a shapefile and making a plot, but building something that fetches, processes, and renders everything from source. The four-level caching pipeline, modular `src/` layout, and orchestrated notebook, version-controlled in GitHub, are deliberate overengineering -- that was the personal challenge I set myself. On my web development course I went down a similar rabbit hole building Conway's Game of Life for fun.

There's a third element: I wanted to trial using an AI assistant as a project-management scaffold for a longer-running piece of work. A known problem in software development that relies heavily on AI is managing the context window -- keeping the model oriented across sessions, preventing drift, maintaining a shared understanding of where things are. I was curious whether intentional workflows (a session log, a decision ledger, a project document that gets pasted at the start of each new chat) could make that tractable. This project was a good candidate to find out. It turned out to be useful well beyond the code itself -- less about generating output, more about having an external system that holds the thread.

### Project structure
```
src/
├── data/        -- WFS and COG fetching, with caching
├── maps/        -- one module per map, plus styles,
│                   PDF assembly, and orchestration
└── processing/  -- terrain and vector helpers
main.ipynb           -- two cells: API key input, then run()
local_resources/     -- created at runtime; DEM tiles and vector cache
output/              -- created at runtime; rendered PNGs and final PDF
```

### Working with Claude

This project was built collaboratively with Claude -- Claude Code for file editing, Claude Chat for design discussion and direction. I also wanted an excuse to learn to use Claude Code properly -- it's highly regarded among people I know in the software industry, and I was curious whether the reality matched the reputation.

Before any code was written, I had already done the groundwork in QGIS: found the data sources, sketched the layouts, and tested fetch approaches and basic plotting in scratch Jupyter notebooks. Everything was working but messy and disconnected. The Claude collaboration was about assembling it into a coherent, structured codebase.

The workflow was close to product ownership. I came in with domain knowledge of geospatial data, a clear idea of what I wanted to build, and an understanding of what good code structure looks like. Claude Code did a lot of the heavy lifting -- especially refactoring and making coordinated edits across multiple files. Claude Chat and I discussed algorithms, projection choices, data source tradeoffs, and debugging approaches, often going both ways. I tested everything in Jupyter, caught the bugs that slipped through, made the design calls, and maintained a detailed session log and decision ledger -- the .ai/ directory in this repo -- so context could be rebuilt cleanly when chat threads became too long to be reliable.

The interesting problems -- why LAEA broke at the antimeridian, why `fetch_layer()` was silently dropping data due to a hardcoded CRS in the bbox suffix, why `layer-51153` returned geographic coordinates when everything downstream expected NZTM -- were diagnosed collaboratively. Some caught by me, some by Claude, most by both looking at the same evidence.

All code has been reviewed and tested by me. Where patterns looked overly complex or hard to explain, I refactored them -- the goal was a codebase I could interrogate and defend, not just one that runs. In an era where code can be copied from Stack Overflow, generated by AI, borrowed from tutorials, or abstracted away inside libraries that no one is expected to read line by line, the more meaningful bar -- from what I understand -- is whether you understood it well enough to test it end-to-end, catch the bugs, and make the design calls. That's what I've tried to do here.

## Known issues

### Runtime warnings

* **PDF preview** -- works on the uni's ondemand JupyterLab server (an AVD/RemoteApp setup), but apparently not on local conda environments, at least not mine. The notebook is meant to display the assembled PDF inline; if it doesn't, just navigate to the file in `/output/`.
* **Shapely `normalize` RuntimeWarning** -- present in my local dev environment and a fresh conda install, absent on the uni server. Some kind of Shapely--GDAL version interaction. Doesn't affect output. Ignored.
* **`GDAL_DATA` not set** -- appears on my dev env and on fresh conda environments, not on the uni server. Something about how GDAL locates its data files. Zero impact. Ignored.

### Tech debt

The architecture isn't ideal. The codebase started as a Jupyter notebook with fetch, processing, and rendering all inline, got modularised into shared modules, then had the details polished -- never stepping back to ask "how should this really be built now." Classic tech debt. Two examples:

**LINZ API key via environment variable.** The original idea was to pull the key from a `LINZ_API_KEY` env var set in my shell -- nothing written down in code anywhere, no risk of accidentally pushing it to GitHub. Got that working. But it's overkill for a single-user assignment, so I pivoted to a simpler "paste your key into the notebook" surface. The internals didn't change to match: `linz.py` still reads from the env var, and `orchestrate.py` now sets the var from the pasted-in key before importing anything that touches `linz.py`. That import-ordering constraint is the visible shape of the tech debt. The cleaner refactor is to have `linz.py` take the key as a parameter. Low priority -- not broken.

**Each map module calls its own data fetches.** The actual fetching -- LINZ, GDC, DEM, Natural Earth -- lives in `src/data/`. But each map module in `src/maps/` has a `fetch_*_data()` function that calls those data modules in the right order and handles the prep work (reprojection, CRS normalisation). Cleaner would be to move that out, so the map modules only draw. The visible cost shows up in `orchestrate.py`: progress messages can only report "fetching maunga data" as a single step, rather than each underlying fetch as it happens. Same story -- not pretty, but it works.

---
This is a public copy of the original working repository, which was never intended for publication. History starts at the public release.

*GISC401 -- University of Canterbury, 2026 -- Zak*