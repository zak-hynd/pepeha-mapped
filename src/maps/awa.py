"""
Renders the awa map (page 3 of the PDF) -- LINZ Wairau river lines and polygons over a tinted DEM hillshade, with NZ locator inset.
Second of the three pepeha-element maps.
For swimming, Canterbury's rivers have nothing on Wairau -- I first scuba dived here"""

import numpy as np
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib import patheffects as pe
from matplotlib.figure import Figure

from src.data.dem import fetch_dem
from src.data.linz import fetch_wairau_rivers
from src.processing.terrain import compute_hillshade
from src.processing.vector import prepare_rivers
from src.maps.common import add_inset, add_scalebar, add_north_arrow
from src.maps.styles import PALETTE, FONTS, SIZES, FIGSIZE, style_map_axes

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# fetch extent (WGS84) -- slightly wider than display to avoid DEM edge gaps
_BBOX_WGS84 = [172.5, -42.6, 174.3, -41.1]

# display extent (NZTM2000)
_XMIN, _XMAX = 1_574_000, 1_708_000
_YMIN, _YMAX = 5_312_000, 5_446_000

# river linewidths
# axes: stem (Wairau main) vs trib (tributaries), line (centreline) vs bound (polygon edge), dark (top) vs glow (under-pass)
_LW = {
    "stem_dark":       0.45,
    "trib_dark":       0.65,
    "stem_bound_dark": 0.50,
    "trib_bound_dark": 0.50,
    "stem_glow":       1.4,
    "trib_glow":       2.1,
    "stem_bound_glow": 2.8,
    "trib_bound_glow": 2.1,
}
_GLOW_ALPHA = 0.70 # tuned to balance visibility of the glow without overpowering the dark line on top


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _plot_rivers(
    ax: plt.Axes,
    stem_lines,
    trib_lines,
    stem_bounds,
    trib_bounds,
) -> None:
    """Two-pass river render: wide pale glow underneath, dark line on top"""
    rg = PALETTE["awa"]
    rd = PALETTE["water"]

    # glow pass
    if not stem_bounds.empty:
        stem_bounds.plot(ax=ax, color=rg, linewidth=_LW["stem_bound_glow"],
                         alpha=_GLOW_ALPHA, zorder=3)
    if not trib_bounds.empty:
        trib_bounds.plot(ax=ax, color=rg, linewidth=_LW["trib_bound_glow"],
                         alpha=_GLOW_ALPHA, zorder=3)
    if not trib_lines.empty:
        trib_lines.plot(ax=ax, color=rg, linewidth=_LW["trib_glow"],
                        alpha=_GLOW_ALPHA, zorder=3)
    if not stem_lines.empty:
        stem_lines.plot(ax=ax, color=rg, linewidth=_LW["stem_glow"],
                        alpha=_GLOW_ALPHA, zorder=3)

    # dark line pass
    if not stem_bounds.empty:
        stem_bounds.plot(ax=ax, color=rd, linewidth=_LW["stem_bound_dark"],
                         zorder=4)
    if not trib_bounds.empty:
        trib_bounds.plot(ax=ax, color=rd, linewidth=_LW["trib_bound_dark"],
                         zorder=4)
    if not trib_lines.empty:
        trib_lines.plot(ax=ax, color=rd, linewidth=_LW["trib_dark"], zorder=4)
    if not stem_lines.empty:
        stem_lines.plot(ax=ax, color=rd, linewidth=_LW["stem_dark"], zorder=5)


def _label_wairau(ax: plt.Axes, stem_lines) -> None:
    """place a 'Te Awa o Wairau' label beside over North Bank / Lake Chalice"""
    if stem_lines.empty:
        return
    stem = stem_lines.geometry.iloc[0]
    if stem.geom_type == "MultiLineString":
        stem = max(stem.geoms, key=lambda g: g.length) # stem may be a MultiLineString after the LINZ merge; longest piece is the central one
    mid = stem.interpolate(0.5, normalized=True)
    ax.text(
        mid.x - 7_000, mid.y - 1_000, # hand-tuned offset to sit alongside a straighter section of the river
        "Te Awa o Wairau",
        color=PALETTE["platinum"],
        fontsize=SIZES["label_md"],
        fontweight="bold",
        fontfamily=FONTS["serif"],
        ha="left", va="bottom",
        rotation=25, rotation_mode="anchor", #parallel to river angle
        zorder=6,
        path_effects=[pe.withStroke(linewidth=3, foreground=PALETTE["ink"], alpha=0.7)],
    )


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def fetch_awa_data() -> dict:
    """fetch DEM tiles and Wairau river data (LINZ lines + polygons); uses disk cache where available"""
    dem = fetch_dem(_BBOX_WGS84, resolution=90)
    dem = dem.rio.reproject("EPSG:2193")

    lines, polys = fetch_wairau_rivers()

    return {"dem_data": dem, "rivers_lines": lines, "rivers_polys": polys}


def render_awa(data: dict) -> Figure:
    """render the Wairau awa map from pre-fetched data and return a Figure"""
    dem = data["dem_data"]
    lines = data["rivers_lines"]
    polys = data["rivers_polys"]

    # 1. extract elevation array and image extent
    elev = dem.values.squeeze().astype(float)
    left, bottom, right, top = dem.rio.bounds()
    img_extent = [left, right, bottom, top]

    # 2. greyscale hillshade + earth-green tint wash
    nan_mask = (~np.isfinite(elev)) | (elev <= 0)
    elev_filled = np.where(nan_mask, 0.0, elev)

    hs = compute_hillshade(elev_filled, dx_m=90.0)
    hs = np.clip(hs * 0.4, 0.0, 1.0) # adjust hillshade contrast, dim to 40% brightness
    hs_rgba = plt.cm.gray(hs)
    hs_rgba[nan_mask, 3] = 0.0

    tint = mcolors.to_rgba(PALETTE["land"])
    tint_alpha = 0.35 # hand-tuned: visible green wash without killing the hillshade
    land_px = ~nan_mask
    # alpha-composite: each land pixel becomes (1-tint_alpha) * original + tint_alpha * tint, per channel
    # ocean pixels are excluded by land_px, so they keep their upstream alpha=0 and stay transparent
    for ch in range(3):
        hs_rgba[land_px, ch] = (
            (1 - tint_alpha) * hs_rgba[land_px, ch] + tint_alpha * tint[ch]
        )

    # 3. process rivers
    # LINZ named-rivers layers are the only NZ-wide source with usable centrelines at this scale;
    # Natural Earth is too generalised, and LINZ's unnamed centreline layers has too many features to
    # filter cleanly. prepare_rivers() merges the two LINZ layers (centrelines + polygons) into the
    # four layers the two-pass render expects.
    stem_lines, trib_lines, stem_bounds, trib_bounds = prepare_rivers(
        lines, polys, main_stem_name="Wairau River"
    )

    # 4. figure and axes
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.set_facecolor(PALETTE["water"])
    fig.patch.set_facecolor(PALETTE["ink"])

    # 5. plot hillshade
    ax.imshow(hs_rgba, extent=img_extent, origin="upper", zorder=1)

    # 6. plot rivers
    _plot_rivers(ax, stem_lines, trib_lines, stem_bounds, trib_bounds)

    # 7. Wairau label
    _label_wairau(ax, stem_lines)

    # 8. map extent
    ax.set_xlim(_XMIN, _XMAX)
    ax.set_ylim(_YMIN, _YMAX)
    ax.set_aspect("equal")
    style_map_axes(ax)

    # 9. scale bar and north arrow
    add_scalebar(ax, length_km=25) # 25km is a good round number that fits the map scale well
    add_north_arrow(ax)

    # 10. inset
    add_inset(fig, ax, (_XMIN, _XMAX), (_YMIN, _YMAX), rect_color=PALETTE["awa"])

    return fig


def make_awa_map() -> Figure:
    """fetch data and render the awa map; thin wrapper for backwards compatibility"""
    return render_awa(fetch_awa_data())
