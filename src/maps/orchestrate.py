"""
The pipeline controller -- validates the LINZ API key, sequentially calls each map module's 
fetch and render functions, saves PNGs to output/, and calls assemble_pdf to produce the PDF.
Called from main.ipynb, hopefully after a LINZ API key is pasted into the _key variable there..."""

import os # needed to write the LINZ API key into the environment before src imports read it (see README Known Issues)
from pathlib import Path  # for more convenient path handling
import matplotlib.pyplot as plt

_OUT_DIR = Path("output") # directory for all rendered PNGs and the final PDF
_PDF_NAME = "GISC401-MapYourPepeha-2026-Z.Hynd.pdf" # changed a few times during dev, easier to change here
_RENDER_DPI = 250  # tuned for crisp labels at PDF page size without bloating render time or file size


def run(api_key: str = "") -> None: 
    """Fetch all geodata, render all maps, and assemble the pepeha PDF.

    The LINZ API key is written into os.environ before src.maps / src.data imports run, 
    because linz.py reads the environment at import time. That coupling is 
    technical debt; see README Known Issues
    """
    # ---------------------------------------------------------------------------
    # API key guard -- must happen before any src.maps / src.data imports
    # ---------------------------------------------------------------------------
    if api_key:  # linz.py reads os.environ at import time, so it must be set first
        os.environ["LINZ_API_KEY"] = api_key 

    if not api_key:
        print(
            "No LINZ API key found.\n"
            "Paste your key between the quotes in cell 1, then re-run.\n"
            "To get a free key: log in at https://data.linz.govt.nz, open your profile\n"
            "menu (top-right) and select API Keys, or go directly to\n"
            "https://data.linz.govt.nz/my/api/"
        )
        raise SystemExit("LINZ API key required - stopping here.")

    # module imports are deferred until after the API key is written to the environment
    from src.maps import styles
    from src.maps.maunga import fetch_maunga_data, render_maunga
    from src.maps.awa import fetch_awa_data, render_awa
    from src.maps.iwi import fetch_iwi_data, render_iwi
    from src.maps.globe import fetch_globe_data, render_globe, render_globe_clean
    from src.maps.pdf_assembly import assemble_pdf

    styles.apply_theme() # set matplotlib global defaults (fonts, colours, background) once for the whole session

    # ---------------------------------------------------------------------------
    # Fetch data for each map
    # ---------------------------------------------------------------------------
    # on the fetching order: iwi is the heaviest pull; failing here saves the time of the other three
    print("Fetching Rongowhakaata rohe, coastline, and DEM (iwi)...")
    data_iwi = fetch_iwi_data()
    print("  ✓ iwi data ready (rohe, coastline, DEM)")

    print("Fetching DEM and NZ outline (maunga)...")
    data_maunga = fetch_maunga_data()
    print("  ✓ maunga data ready (DEM, NZ outline)")

    print("Fetching DEM and Wairau river network (awa)...")
    data_awa = fetch_awa_data()
    print("  ✓ awa data ready (DEM, river lines, river polygons)")

    print("Fetching Natural Earth countries and NZ outline (globe)...")
    data_globe = fetch_globe_data()
    print("  ✓ globe data ready (countries, NZ outline)")

    # ---------------------------------------------------------------------------
    # Render -- save each figure to output/ then close it
    # ---------------------------------------------------------------------------
    _OUT_DIR.mkdir(exist_ok=True) # ensure output/ exists before trying to save files there

    print("Rendering maunga map...")
    fig = render_maunga(data_maunga)
    fig.savefig(_OUT_DIR / "maunga.png", dpi=_RENDER_DPI, facecolor=fig.get_facecolor())
      # ^^ facecolor must be passed explicitly -- savefig() defaults to white otherwise
    plt.close(fig) # release figure memory immediately after saving -- prevents accumulation across five render calls
    print("  ✓ maunga map rendered")

    print("Rendering awa map...")
    fig = render_awa(data_awa)
    fig.savefig(_OUT_DIR / "awa.png", dpi=_RENDER_DPI, facecolor=fig.get_facecolor())
    plt.close(fig)
    print("  ✓ awa map rendered")

    print("Rendering iwi map...")
    fig = render_iwi(data_iwi)
    fig.savefig(_OUT_DIR / "iwi.png", dpi=_RENDER_DPI, facecolor=fig.get_facecolor())
    plt.close(fig)
    print("  ✓ iwi map rendered")

    print("Rendering opening globe...")
    fig = render_globe_clean(data_globe)
    fig.savefig(_OUT_DIR / "globe_clean.png", dpi=_RENDER_DPI, facecolor=fig.get_facecolor())
    plt.close(fig)
    print("  ✓ opening globe rendered")

    print("Rendering closing globe...")
    fig = render_globe(data_globe)
    fig.savefig(_OUT_DIR / "globe_annotated.png", dpi=_RENDER_DPI, facecolor=fig.get_facecolor())
    plt.close(fig)
    print("  ✓ closing globe rendered")

    # ---------------------------------------------------------------------------
    # Assemble PDF
    # ---------------------------------------------------------------------------
    png_paths = {
        "globe_clean":     _OUT_DIR / "globe_clean.png",
        "maunga":          _OUT_DIR / "maunga.png",
        "awa":             _OUT_DIR / "awa.png",
        "iwi":             _OUT_DIR / "iwi.png",
        "globe_annotated": _OUT_DIR / "globe_annotated.png",
    }
    out_path = _OUT_DIR / _PDF_NAME

    print("Assembling PDF...")
    assemble_pdf(png_paths, out_path)
    print(f"  ✓ {_PDF_NAME} saved to output/")

    # ---------------------------------------------------------------------------
    # display the finished PDF inline in the notebook and provide a download link
    # ---------------------------------------------------------------------------
    # note: IFrame PDF rendering works on the uni's ondemand JupyterLab server but may not render in local Jupyter environments
    from IPython.display import IFrame, FileLink, display
    display(IFrame(str(out_path), width=800, height=1000)) # 4:5 roughly approximates A4 portrait at a notebook-friendly width
    display(FileLink(str(out_path))) # clickable download link -- use this if IFrame doesn't render