"""
Shared map furniture used by every map module -- provides the NZTM projection constant, 
add_inset(), add_scalebar(), and add_north_arrow(), plus load_nz_outline() which downloads 
and caches a filtered NZ land polygon used by all insets.
Imported by every map module; load_nz_outline() runs once from main.ipynb at startup, the 
others are called per-map."""

import matplotlib.patches as mpatches
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from pathlib import Path
import geopandas as gpd
from shapely.geometry import box

from src.data.natural_earth import fetch_land_polygons
from src.maps.styles import PALETTE, FONTS, SIZES

# ---------------------------------------------------------------------------
# Projection constant -- used by every map module
# ---------------------------------------------------------------------------

NZTM = "EPSG:2193"

# scalebar and north arrow geometry; both functions read from here.
# edit these to reposition or resize the furniture; both elements move together.
_SB_X    = 0.075   # scalebar left edge (axes fraction)
_SB_Y    = 0.030   # scalebar bottom edge (axes fraction)
_SB_H    = 0.022   # scalebar height (axes fraction)
_NA_X    = 0.040   # north arrow centre-x (axes fraction)
_NA_LIFT = 0.0025  # north arrow nudge above scalebar vertical centre

# paths to local resources; avoids hardcoding paths, which might differ between users and environments
_PROJECT_ROOT = Path(__file__).resolve().parents[2] # two levels up from src/maps/ → project root
_LOCAL_RESOURCES = _PROJECT_ROOT / "local_resources"

# path to the pre-built NZ outline file, written once by load_nz_outline().
_NZ_OUTLINE_PATH = _LOCAL_RESOURCES / "natural_earth" / "nz_outline.gpkg"

# NZ extent in NZTM2000 -- used to set the inset view window (excludes the Chathams)
_NZ_XLIM = (1_050_000, 2_150_000)
_NZ_YLIM = (4_700_000, 6_250_000)

# NZ clip box in WGS84 -- used during load_nz_outline() to trim world land (also excl. Chathams)
_NZ_BBOX_WGS84 = box(165.0, -47.5, 178.5, -34.0)

# minimum island area to keep: 100 km² in m² (EPSG:2193 units)
# threshold drops the small offshore specks but keeps NI, SI, Rakiura, & other larger islands
# calculated in EPSG:2193 to avoid the geographic-CRS area warning
_MIN_ISLAND_AREA_M2 = 100e6


# ---------------------------------------------------------------------------
# Setup function -- called once from main.ipynb at notebook startup
# ---------------------------------------------------------------------------

def load_nz_outline() -> None:
    """download NZ land polygons, filter to islands >100 km², save to local_resources/nz_outline.gpkg
    Run once from main.ipynb at startup; the cached file is read by add_inset() on every map.
    See _MIN_ISLAND_AREA_M2 for the threshold rationale.
    """
    land = fetch_land_polygons(crs="EPSG:4326")
    nz = gpd.clip(land, _NZ_BBOX_WGS84)
    nz = nz.to_crs(NZTM)
    nz = nz[nz.geometry.area >= _MIN_ISLAND_AREA_M2].copy()
    _NZ_OUTLINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    nz.to_file(_NZ_OUTLINE_PATH, driver="GPKG")


# ---------------------------------------------------------------------------
# Inset map
# ---------------------------------------------------------------------------

def add_inset(
    fig: Figure,
    main_ax: Axes,
    main_xlim: tuple[float, float],
    main_ylim: tuple[float, float],
    rect_color: str = PALETTE["platinum"], # this is overridden with the caller module's narrative colour (maunga/awa/iwi)
) -> Axes:
    """add a NZ locator inset anchored inside the main axes bounds.
    
    Two coordinate systems in play: the inset axes is positioned in figure fractions, computed 
    from main_ax.get_position() so it tracks the main axes regardless of layout. The locator 
    rectangle inside is drawn in NZTM data coordinates -- the inset is in NZTM too, so main_xlim 
    and main_ylim go straight in
    """
    pos = main_ax.get_position()
    # inset proportions and offsets are hand-tuned to sit in the bottom-right corner of the main axes
    inset_w = 0.26 * pos.width
    inset_h = 0.30 * pos.height
    inset_left   = pos.x0 + pos.width - inset_w + 0.02 * pos.width
    inset_bottom = pos.y0 + 0.01 * pos.height
    position = [inset_left, inset_bottom, inset_w, inset_h]

    nz = gpd.read_file(_NZ_OUTLINE_PATH)

    ax_ins = fig.add_axes(position)
    ax_ins.set_xlim(_NZ_XLIM)
    ax_ins.set_ylim(_NZ_YLIM)
    ax_ins.set_aspect("equal")
    ax_ins.axis("off")

    ax_ins.patch.set_visible(True)
    ax_ins.patch.set_facecolor(PALETTE["ink"])

    nz.plot(ax=ax_ins, color=PALETTE["land"], edgecolor="none")

    # halo effect: thick dark outer rect at low alpha sits behind a thin coloured inner rect
    # keeps the locator box readable on both light land and dark ocean in the inset
    rect_outer = mpatches.Rectangle(
        (main_xlim[0], main_ylim[0]),
        main_xlim[1] - main_xlim[0],
        main_ylim[1] - main_ylim[0],
        linewidth=3.0,
        edgecolor=PALETTE["ink"],
        alpha=0.6,
        facecolor="none",
        zorder=5,
    )
    rect_inner = mpatches.Rectangle(
        (main_xlim[0], main_ylim[0]),
        main_xlim[1] - main_xlim[0],
        main_ylim[1] - main_ylim[0],
        linewidth=1.2,
        edgecolor=rect_color,
        facecolor="none",
        zorder=6,
    )
    ax_ins.add_patch(rect_outer)
    ax_ins.add_patch(rect_inner)

    for spine in ax_ins.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.8)
        spine.set_edgecolor(PALETTE["platinum"])

    return ax_ins


# ---------------------------------------------------------------------------
# Scale bar
# ---------------------------------------------------------------------------

def add_scalebar(ax: Axes, length_km: float) -> None:
    """draw a scale bar with label, bottom-left of the map"""
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    xr = xlim[1] - xlim[0]
    # anchor the bar at _SB_X in axes fractions, then size it from the caller-supplied physical length
    x0 = xlim[0] + _SB_X * xr
    x1 = x0 + length_km * 1000
    y0 = ylim[0] + _SB_Y * (ylim[1] - ylim[0])
    h  = _SB_H * (ylim[1] - ylim[0])
    ax.add_patch(mpatches.Rectangle(
        (x0, y0), x1 - x0, h,
        facecolor=PALETTE["ink"], edgecolor=PALETTE["platinum"],
        linewidth=0.75, transform=ax.transData, zorder=5, # coordinates in NZTM metres; width = real distance
    ))
    ax.text(
        (x0 + x1) / 2, y0 + h * 0.45, f"{length_km:.0f} km", # 0.45 not 0.5 -- optical centring; text reads as centred when nudged slightly down
        ha="center", va="center", fontsize=SIZES["scalebar"],
        color=PALETTE["platinum"], fontweight="semibold",
        transform=ax.transData, zorder=6,
    )


# ---------------------------------------------------------------------------
# North arrow
# ---------------------------------------------------------------------------

def add_north_arrow(ax: Axes) -> None:
    """draw a chevron north arrow in axes fractions, beside the scale bar"""
    cx = _NA_X
    cy = _SB_Y + _SB_H / 2 + _NA_LIFT  # vertically centred on scalebar
    h  = _SB_H * 1.8   # slightly taller than scalebar for visual balance
    w  = h * 0.8        # chevron width
    n  = h * 0.1        # notch depth -- pulls bottom-centre up for chevron shape
    ax.add_patch(mpatches.Polygon(
        [[cx,       cy + h * 0.55 ],   # tip
         [cx - w/2, cy - h * 0.45 ],   # bottom-left
         [cx,       cy - h * 0.45 + n],# notch
         [cx + w/2, cy - h * 0.45 ]],  # bottom-right
        closed=True, facecolor=PALETTE["ink"], edgecolor=PALETTE["platinum"],
        linewidth=0.75, transform=ax.transAxes, zorder=7, # coordinates in axes fractions; fixed position regardless of map extent
    ))
    ax.text(
        cx - 0.0005, cy - h * 0.16, "N",  # tiny x-nudge and y-offset to optically centre the N inside the chevron
        ha="center", va="center", fontsize=SIZES["scalebar"],
        color=PALETTE["platinum"], fontweight="semibold",
        transform=ax.transAxes, zorder=9,
    )
