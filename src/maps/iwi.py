"""
Renders the iwi map (page 4 of the PDF) -- Rongowhakaata rohe polygon over a green-tinted DEM hillshade, with NZ locator inset
Third of the three pepeha-element maps.
I should really visit Gisborne some day -- it's probably the only part of the country I've never been to!"""

import numpy as np
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib import patheffects as pe
from matplotlib.figure import Figure

from src.data.dem import fetch_dem
from src.data.gdc import fetch_rongowhakaata_aoi
from src.data.linz import fetch_layer
from src.processing.terrain import compute_hillshade
from src.maps.common import NZTM, add_inset, add_scalebar, add_north_arrow
from src.maps.styles import PALETTE, FONTS, SIZES, FIGSIZE, style_map_axes

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# fetch extent (WGS84) -- slightly wider than display to avoid DEM edge gaps
_BBOX_WGS84 = [177.0, -39.4, 178.7, -38.1]

# display extent (NZTM2000)
_XMIN, _XMAX = 1_951_000, 2_072_000
_YMIN, _YMAX = 5_635_000, 5_756_000

# coastline fetch bbox: full display extent + 10 km pad on each side (NZTM2000)
_COAST_BBOX = [_XMIN - 10_000, _YMIN - 10_000, _XMAX + 10_000, _YMAX + 10_000]

# GDC layer land feature names -- "Rongo AOI" is the main rohe, "Pecked" covers the peninsula/Gisborne city; "Coastal Marine Area" excluded
_LAND_NAMES = {"Rongo AOI", "Pecked"}


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def fetch_iwi_data() -> dict:
    """fetch Rongowhakaata polygon, LINZ coastline, and DEM tiles for the iwi map"""
    iwi = fetch_rongowhakaata_aoi()
    if iwi.crs is None or iwi.crs.to_epsg() != 2193:
        iwi = iwi.to_crs(NZTM)

    coast = fetch_layer(
        "layer-51153", crs=NZTM, bbox=_COAST_BBOX,
        bbox_crs="EPSG:2193", max_features=500,
    )
    if coast.crs is None or coast.crs.to_epsg() != 2193:
        coast = coast.to_crs(NZTM)

    dem = fetch_dem(_BBOX_WGS84, resolution=90)
    dem = dem.rio.reproject("EPSG:2193")

    return {"iwi_poly": iwi, "coastline": coast, "dem_data": dem}


def render_iwi(data: dict) -> Figure:
    """Render the Rongowhakaata iwi map from pre-fetched data and return a Figure
    
    Layered drawing order: hillshade-blended DEM, rohe polygon & label,
    style/scalebar/north arrow, inset locator. Called from orchestrate.run()
    to produce iwi.png for page 4."""
    iwi = data["iwi_poly"]
    coast = data["coastline"]
    dem = data["dem_data"]

    # 1. filter to land features only
    iwi = iwi[iwi["NAME"].isin(_LAND_NAMES)].copy()

    # 2. clip rohe features to the LINZ land polygon -- trims an ocean overhang on the main "Rongo AOI" part
    coast_poly = coast[coast.geometry.geom_type.isin(["Polygon", "MultiPolygon"])] # LINZ layer-51153 should be polygons-only; defensive against mixed-geom edge cases
    iwi_land = iwi.overlay(coast_poly, how="intersection")

    # 3. dissolve to merge Rongo AOI + Pecked into one geometry
    iwi_land = iwi_land.dissolve()
    land_geom = iwi_land.geometry.iloc[0]

    # 4. extract elevation array and compute greyscale hillshade
    elev = dem.values.squeeze().astype(float)
    left, bottom, right, top = dem.rio.bounds()
    img_extent = [left, right, bottom, top]

    nan_mask = (~np.isfinite(elev)) | (elev <= 0)
    elev_filled = np.where(nan_mask, 0.0, elev)

    hs = compute_hillshade(elev_filled, dx_m=90.0)
    hs = np.clip(hs * 0.4, 0.0, 1.0) # adjust hillshade contrast, dim to 40% brightness
    hs_rgba = plt.cm.gray(hs)
    hs_rgba[nan_mask, 3] = 0.0

    # blend tint wash into hillshade on land pixels only
    tint = mcolors.to_rgba(PALETTE["land"])
    tint_alpha = 0.35 # hand-tuned: visible green wash without smothering the hillshade
    land_px = ~nan_mask

    # alpha-composite: each land pixel becomes (1-tint_alpha) * original + tint_alpha * tint, per channel
    # ocean pixels are excluded by land_px, so they keep their upstream alpha=0 and stay transparent
    for ch in range(3):
        hs_rgba[land_px, ch] = (
            (1 - tint_alpha) * hs_rgba[land_px, ch] + tint_alpha * tint[ch]
        )

    # 5. figure and axes
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.set_facecolor(PALETTE["water"])
    fig.patch.set_facecolor(PALETTE["ink"])

    # 6. plot hillshade
    ax.imshow(hs_rgba, extent=img_extent, origin="upper", zorder=1)

    # 7. plot iwi polygon
    iwi_land.plot(
        ax=ax,
        facecolor=PALETTE["iwi"],
        edgecolor=PALETTE["platinum"],
        linewidth=1.0,
        alpha=0.65, # fill is translucent so the underlying terrain still shows through
        zorder=2,
    )

    # 8. centroid label
    centroid = land_geom.centroid
    ax.text(
        centroid.x, centroid.y,
        "Rongowhakaata\nRohe",
        color=PALETTE["platinum"], fontsize=SIZES["label_md"], fontweight="bold",
        fontfamily=FONTS["serif"],
        ha="center", va="center", zorder=3,
        path_effects=[pe.withStroke(linewidth=3, alpha=0.7, foreground=PALETTE["ink"])],
    )

    # 9. map extent and tick labels
    ax.set_xlim(_XMIN, _XMAX)
    ax.set_ylim(_YMIN, _YMAX)
    ax.set_aspect("equal")
    style_map_axes(ax)

    # 10. scale bar and north arrow
    add_scalebar(ax, length_km=25) # 25 km is a good round number that fits well within the scene
    add_north_arrow(ax)

    # 11. inset
    add_inset(fig, ax, (_XMIN, _XMAX), (_YMIN, _YMAX), rect_color=PALETTE["iwi"])

    return fig


def make_iwi_map() -> Figure:
    """fetch data and render the iwi map; thin wrapper for backwards compatibility"""
    return render_iwi(fetch_iwi_data())
