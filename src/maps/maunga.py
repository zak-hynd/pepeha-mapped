"""
Renders the maunga map (page 2 of the PDF) -- DEM hillshade with the inferno colourmap, summit marker, NZ locator inset.
First of the three pepeha-element maps.Tapuae-O-Uenuku, the footprint of Uenuku (the rainbow god) -- but no rainbow colourmaps are allowed... if this were InSAR, maybe, but I would hope that were a perceptually-uniform rainbow, not jet, but better still, a perceptually-uniform cyclic one...
I digress..."""


from pathlib import Path

import geopandas as gpd
import numpy as np
import matplotlib
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource, Normalize
from matplotlib.figure import Figure
from matplotlib import patheffects as pe

from src.data.dem import fetch_dem
from src.processing.terrain import compute_hillshade
from src.maps.common import add_inset, add_scalebar, add_north_arrow, load_nz_outline
from src.maps.styles import (
    PALETTE, FONTS, SIZES, FIGSIZE, style_map_axes,
    MAUNGA_CMAP_NAME, MAUNGA_CMAP_LO, MAUNGA_CMAP_HI,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


# fetch extent (WGS84) -- slightly wider than display to avoid DEM edge gaps
_BBOX_WGS84 = [173.0, -42.6, 174.1, -41.5]

# display extent (NZTM2000) -- covers Tapuae-O-Uenuku and surrounding Kaikōura Ranges
_XMIN, _XMAX = 1_622_000, 1_690_000
_YMIN, _YMAX = 5_301_000, 5_369_000

# summit location in NZTM2000 (~173.663°E, 41.996°S)
_SUMMIT_E = 1_655_490
_SUMMIT_N = 5_350_472

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_NZ_OUTLINE_PATH = _PROJECT_ROOT / "local_resources" / "natural_earth" / "nz_outline.gpkg"


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def fetch_maunga_data() -> dict:
    """fetch DEM tiles and NZ outline for the maunga map; uses disk cache where available"""
    if not _NZ_OUTLINE_PATH.exists():
        load_nz_outline()
    nz_outline = gpd.read_file(_NZ_OUTLINE_PATH)

    dem = fetch_dem(_BBOX_WGS84, resolution=90)
    dem = dem.rio.reproject("EPSG:2193")

    return {"dem_data": dem, "nz_outline": nz_outline}


def render_maunga(data: dict) -> Figure:
    """Render the Tapuae-O-Uenuku maunga map from pre-fetched data, return a Figure.

    Layered drawing order: hillshade-blended DEM, summit marker + label,
    style/scalebar/north arrow, inset locator. Called from orchestrate.run()
    to produce maunga.png for page 2."""
    dem = data["dem_data"]

    # 1. extract elevation array and image extent
    elev = dem.values.squeeze().astype(float)
    left, bottom, right, top = dem.rio.bounds()
    img_extent = [left, right, bottom, top]

    # 2. blend elevation colormap + hillshade
    nan_mask = (~np.isfinite(elev)) | (elev <= 0)
    elev_filled = np.where(nan_mask, 0.0, elev)

    ls = LightSource(azdeg=315, altdeg=45) # hillshade parameters: light from NW at 45° above horizon
    
    # clip inferno to [MAUNGA_CMAP_LO, MAUNGA_CMAP_HI] so the warm tones span the whole scene, not just the peaks.
    # LinearSegmentedColormap.from_list() is necessary here because ls.shade() has no vmin/vmax equivalent.
    _cmap_full = matplotlib.colormaps[MAUNGA_CMAP_NAME]
    _norm = Normalize(
        vmin=elev_filled[~nan_mask].min() if (~nan_mask).any() else 0,
        vmax=elev_filled.max(),
    )
    _cmap_clipped = mcolors.LinearSegmentedColormap.from_list(
        "maunga_cmap",
        [_cmap_full(v) for v in np.linspace(MAUNGA_CMAP_LO, MAUNGA_CMAP_HI, 256)],
    )
    rgb = ls.shade(
        elev_filled,
        cmap=_cmap_clipped,
        norm=_norm,
        vert_exag=1.5,  # mild exaggeration
        dx=90.0,        # pixel size in metres -- matches GLO-90 DEM
        dy=90.0,
        blend_mode="overlay",
        fraction=0.5,   # half-strength shade keeps the colormap readable underneath
    )
    rgb[nan_mask, 3] = 0.0

    # 3. figure and axes
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.set_facecolor(PALETTE["water"])
    fig.patch.set_facecolor(PALETTE["ink"])

    # 4. plot DEM
    ax.imshow(rgb, extent=img_extent, origin="upper", zorder=1)

    # 5. summit marker + label
    ax.plot(
        _SUMMIT_E, _SUMMIT_N,
        marker="^", color=PALETTE["maunga"], markersize=8,
        markeredgecolor=PALETTE["ink"], markeredgewidth=0.8, zorder=3,
    )
    ax.text(
        _SUMMIT_E + 800, _SUMMIT_N + 800, # offset label from summit
        "Tapuae-O-Uenuku",
        color=PALETTE["platinum"], fontsize=SIZES["label_md"], fontweight="bold",
        fontfamily=FONTS["serif"],
        va="center", zorder=3,
        path_effects=[pe.withStroke(linewidth=3, alpha=0.7, foreground=PALETTE["ink"])]
    )

    # 6. map extent and style
    ax.set_xlim(_XMIN, _XMAX)
    ax.set_ylim(_YMIN, _YMAX)
    ax.set_aspect("equal")
    style_map_axes(ax)

    # 7. scale bar and north arrow
    add_scalebar(ax, length_km=15) # 15 km is a good round number that fits well within the scene
    add_north_arrow(ax)

    # 8. inset -- NZ locator, bottom-right inside axes
    add_inset(fig, ax, (_XMIN, _XMAX), (_YMIN, _YMAX), rect_color=PALETTE["maunga"])

    return fig


def make_maunga_map() -> Figure:
    """Fetch data and render the maunga map; thin wrapper for backwards compatibility"""
    return render_maunga(fetch_maunga_data())
