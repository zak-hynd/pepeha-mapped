"""
Produces the two globe pages in orthographic projection centred on Ōtautahi -- Natural Earth countries,
painstakingly-constructed graticules, and (in the annotated variant) a Te Waipounamu highlight and Whare Wānanga o Waitaha label.
Called by orchestrate.run(); renders to globe_clean.png (opening page) and globe_annotated.png (closing page)"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import patheffects as pe
from matplotlib.figure import Figure
from pathlib import Path
import geopandas as gpd
from shapely.geometry import Point
from pyproj import Transformer
from src.maps.styles import (
    PALETTE, FONTS, SIZES, FIGSIZE, GLOBE_FIGSIZE,
    GLOBE_GRATICULE_STEP,
    GLOBE_GRATICULE_SAMPLE,
    GLOBE_LAT_LABEL_LON,
    GLOBE_LON_LABEL_LAT,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# orthographic projection centred on CHC/Ōtautahi -- raw PROJ string because orthographic has no EPSG code
ORTHO_PROJ = (
    "+proj=ortho +lat_0=-43.5 +lon_0=172.6 "
    "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs" # no offsets, WGS84 datum, output in metres
)

# Earth's radius in metres; used for the globe boundary circle and axis limits
_EARTH_RADIUS = 6_371_000

# colour aliases -- semantic names that keep the render functions readable without indexing PALETTE directly
SPACE_COLOR     = PALETTE["ink"]
OCEAN_COLOR     = PALETTE["water"]
LAND_COLOR      = PALETTE["land"]
GRATICULE_COLOR = PALETTE["platinum"]
SI_COLOR        = PALETTE["waipounamu"]

# Christchurch in WGS84
_CHCH_LON, _CHCH_LAT = 172.6, -43.5

# Natural Earth GeoJSON URLs (110 m -- lightweight, no API key)
_NE_COUNTRIES_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector"
    "/master/geojson/ne_110m_admin_0_countries.geojson"
)

_PROJECT_ROOT       = Path(__file__).resolve().parents[2]
_NZ_OUTLINE_PATH    = _PROJECT_ROOT / "local_resources" / "natural_earth" / "nz_outline.gpkg"
_NE_CACHE_DIR       = _PROJECT_ROOT / "local_resources" / "natural_earth"
_NE_COUNTRIES_CACHE = _NE_CACHE_DIR / "ne_110m_admin_0_countries.gpkg"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_si(countries_raw: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """extract Te Waipounamu from the NE NZ multi-polygon by filtering exploded parts to centroids
    south of 41°S; needed because the NE 'New Zealand' record bundles the North Island, Chatham
    Islands, and other territories into one feature"""
    nz = countries_raw[countries_raw["SOVEREIGNT"] == "New Zealand"].copy()
    nz_ortho = nz.to_crs(ORTHO_PROJ)
    parts = nz_ortho.explode(index_parts=False).reset_index(drop=True)
    centroids_lat = (
        gpd.GeoDataFrame(geometry=parts.geometry.centroid, crs=ORTHO_PROJ)
        .to_crs("EPSG:4326")
        .geometry.y
    )
    return parts[centroids_lat < -41.0].copy() # 41°S is the conventional NI/SI dividing latitude


def _make_graticules(step: int = 10, sample: float = 0.5) -> list:
    """generate graticule lines manually via pyproj rather than a cartopy gridliner -- the
    orthographic projection needs horizon-aware segment splitting that cartopy doesn't handle cleanly.
    returns a flat list of segment dicts, each with 'coords' (list of (x, y) tuples in ORTHO_PROJ
    metres) and 'major' (bool, True every 20°).
    """
    transformer = Transformer.from_crs(
        "EPSG:4326", ORTHO_PROJ, always_xy=True
    )

    def _project_line(lons, lats):
        xs, ys = transformer.transform(lons, lats)
        segments = []
        current = []
        for x, y in zip(xs, ys):
            # drop points that aren't on the visible hemisphere:
            # - inf/nan: pyproj returns these for points beyond the horizon
            # - distance > 0.999 * Earth radius: at or just past the visible disc
            # when a point fails, close the current segment and start a new one
            if (np.isinf(x) or np.isinf(y) or
                    np.isnan(x) or np.isnan(y) or
                    np.sqrt(x**2 + y**2) > _EARTH_RADIUS * 0.999):
                if len(current) >= 2:
                    segments.append(current)
                current = []
            else:
                current.append((x, y))
        if len(current) >= 2:
            segments.append(current)
        return segments

    all_segments = []

    for lon in np.arange(-180, 180, step):
        major = (int(lon) % 20 == 0)
        lats = np.arange(-89.5, 90, sample)
        lons = np.full_like(lats, float(lon))
        for coords in _project_line(lons, lats):
            all_segments.append({"coords": coords, "major": major})

    for lat in np.arange(-80, 81, step):
        major = (int(lat) % 20 == 0)
        lons = np.arange(-180, 180.5, sample)
        lats = np.full_like(lons, float(lat))
        for coords in _project_line(lons, lats):
            all_segments.append({"coords": coords, "major": major})

    return all_segments


def _graticule_labels(ax: plt.Axes, step: int = 10) -> None:
    """Plot lat and lon graticule labels along anchor lines.

    Two passes: latitude labels along the GLOBE_LAT_LABEL_LON meridian, longitude
    labels along the GLOBE_LON_LABEL_LAT parallel. Labels beyond 75% of Earth
    radius from the projection centre are skipped to avoid horizon clutter.
    """
    transformer = Transformer.from_crs(
        "EPSG:4326", ORTHO_PROJ, always_xy=True
    )
    # skip plotting labels beyond 75% of Earth radius; avoids label-cluttering near the horizon
    limit = 0.75 * _EARTH_RADIUS
    LABEL_LATS = [-70, -50, -30, -10, 10, 30, 50, 70]

    for lat in LABEL_LATS:
        x, y = transformer.transform(GLOBE_LAT_LABEL_LON, lat)
        if np.isinf(x) or np.isnan(x):
            continue
        if (x**2 + y**2) > limit**2:
            continue
        label = f"{abs(lat)}°{'N' if lat >= 0 else 'S'}"
        ax.text(
            x - 80_000, y, label,
            fontsize=SIZES["scalebar"],
            color=PALETTE["platinum"],
            ha="center", va="center",
            fontfamily=FONTS["sans"],
            zorder=8,
            path_effects=[pe.withStroke(linewidth=1.5, foreground=PALETTE["ink"])],
        )

    for lon in range(-180, 180, step * 2):
        x, y = transformer.transform(lon, GLOBE_LON_LABEL_LAT)
        if np.isinf(x) or np.isnan(x):
            continue
        if (x**2 + y**2) > limit**2:
            continue
        if lon == 0:
            label = "0°"
        elif abs(lon) == 180:
            label = "180°"
        elif lon > 0:
            label = f"{lon}°E"
        else:
            label = f"{abs(lon)}°W"
        ax.text(
            x, y, label,
            fontsize=SIZES["scalebar"],
            color=PALETTE["platinum"],
            ha="center", va="top",
            fontfamily=FONTS["sans"],
            zorder=8,
            path_effects=[pe.withStroke(linewidth=1.5, foreground=PALETTE["ink"])],
        )


def _draw_globe_base(
    ax: plt.Axes,
    countries_dissolved: gpd.GeoDataFrame,
    rakiura: gpd.GeoDataFrame,
    grat_segments: list,
) -> Point:
    """draw ocean 'disc', land, graticules, Rakiura, and boundary ring; return globe_circle."""
    globe_circle = Point(0, 0).buffer(_EARTH_RADIUS)

    ax.fill(*globe_circle.exterior.xy, color=OCEAN_COLOR, zorder=1)

    # major graticules (every 20°) get slightly heavier lines and higher alpha -- visual hierarchy on the dark background
    for seg in grat_segments:
        xs, ys = zip(*seg["coords"])
        lw = 0.4 if seg["major"] else 0.25
        alpha = 0.5 if seg["major"] else 0.4
        ax.plot(xs, ys, color=GRATICULE_COLOR, linewidth=lw, alpha=alpha, zorder=2)

    countries_dissolved.plot(
        ax=ax,
        facecolor=PALETTE["land"],
        alpha=0.4,
        edgecolor=PALETTE["platinum"],
        linewidth=0.5,
        zorder=3,
    )

    rakiura.plot(
        ax=ax,
        facecolor=PALETTE["land"],
        alpha=0.25,
        edgecolor=PALETTE["platinum"],
        linewidth=0.5,
        zorder=3,
    )

    ax.plot(
        *globe_circle.exterior.xy,
        color=PALETTE["platinum"], linewidth=0.6, zorder=5,
    )

    return globe_circle


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def fetch_globe_data() -> dict:
    """Fetch Natural Earth countries, NZ outline, and extract Rakiura; no plotting"""
    if not _NE_COUNTRIES_CACHE.exists():
        countries = gpd.read_file(_NE_COUNTRIES_URL)
        _NE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        countries.to_file(_NE_COUNTRIES_CACHE, driver="GPKG")
    else:
        countries = gpd.read_file(_NE_COUNTRIES_CACHE)

    nz_outline = gpd.read_file(_NZ_OUTLINE_PATH)

    # Rakiura (Stewart Island) is missing from NE 110m -- load from nz_outline.gpkg
    # index 19 in the exploded ORTHO_PROJ parts is the third-largest island
    outline_parts = (
        nz_outline.to_crs(ORTHO_PROJ)
        .explode(index_parts=False)
        .reset_index(drop=True)
    )
    rakiura = outline_parts.loc[[19]].copy()
    # 5 km simplify tolerance - Rakiura is small at globe scale, full coastline detail isn't visible anyway
    rakiura.geometry = rakiura.geometry.simplify(5000)

    return {"countries": countries, "nz_outline": nz_outline, "rakiura": rakiura}


def render_globe(data: dict) -> Figure:
    """render the full annotated globe (NZ highlighted, Ōtautahi marker, labels)
    Called from orchestrate.run() to produce globe_annotated.png for page 5."""
    countries_raw = data["countries"]
    rakiura = data["rakiura"]

    countries = countries_raw.dissolve().to_crs(ORTHO_PROJ)
    grat_segments = _make_graticules(GLOBE_GRATICULE_STEP, GLOBE_GRATICULE_SAMPLE)
    si = _extract_si(countries_raw)

    chch_gdf = gpd.GeoDataFrame(
        geometry=[Point(_CHCH_LON, _CHCH_LAT)], crs="EPSG:4326"
    ).to_crs(ORTHO_PROJ)
    chch_x = chch_gdf.geometry.iloc[0].x
    chch_y = chch_gdf.geometry.iloc[0].y

    fig, ax = plt.subplots(figsize=GLOBE_FIGSIZE)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(SPACE_COLOR)
    ax.set_facecolor(SPACE_COLOR)

    _draw_globe_base(ax, countries, rakiura, grat_segments)

    # Te Waipounamu highlight
    si.plot(
        ax=ax,
        color=SI_COLOR,
        edgecolor=PALETTE["platinum"],
        linewidth=0.5,
        zorder=4,
    )

    # Christchurch marker
    ax.plot(
        chch_x, chch_y,
        "o",
        color=PALETTE["wananga"],
        markersize=6,
        markeredgecolor=PALETTE["platinum"],
        markeredgewidth=0.6,
        zorder=6,
    )

    # Te Waipounamu label -- centroid offset NW and rotated 49° to sit along the West Coast
    si_centroid = si.geometry.iloc[0].centroid
    ax.text(
        si_centroid.x - 700_000, si_centroid.y -10_000,
        "       Te\nWaipounamu", # leading spaces optically centre the two-line label
        color=PALETTE["platinum"], fontsize=SIZES["label_md"], fontweight="bold",
        fontfamily=FONTS["serif"],
        ha="center", va="center",
        rotation=49, rotation_mode="anchor",
        zorder=7,
        path_effects=[pe.withStroke(linewidth=3, alpha=0.7, foreground=PALETTE["ink"])],
    )

    # UC/Whare Wānanga o Waitaha label -- offset SE, por la belleza cartografica
    ax.text(
        chch_x + 200_000, chch_y - 100_000,
        "Whare Wānanga\n  o Waitaha",
        color=PALETTE["platinum"], fontsize=SIZES["label_md"], fontweight="bold",
        fontfamily=FONTS["serif"],
        ha="left", va="top", zorder=7,
        path_effects=[pe.withStroke(linewidth=3, alpha=0.7, foreground=PALETTE["ink"])],
    )

    pad = _EARTH_RADIUS * 0.02 # 2% breathing room so the boundary ring isn't flush with the figure edge
    ax.set_xlim(-_EARTH_RADIUS - pad, _EARTH_RADIUS + pad)
    ax.set_ylim(-_EARTH_RADIUS - pad, _EARTH_RADIUS + pad)

    _graticule_labels(ax, GLOBE_GRATICULE_STEP)

    return fig


def render_globe_clean(data: dict) -> Figure:
    """render globe with no NZ highlight, no markers, no text labels
    Called from orchestrate.run() to produce globe_clean.png for page 1."""
    countries_raw = data["countries"]
    rakiura = data["rakiura"]

    countries = countries_raw.dissolve().to_crs(ORTHO_PROJ)
    grat_segments = _make_graticules(GLOBE_GRATICULE_STEP, GLOBE_GRATICULE_SAMPLE)

    fig, ax = plt.subplots(figsize=GLOBE_FIGSIZE)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(SPACE_COLOR)
    ax.set_facecolor(SPACE_COLOR)

    _draw_globe_base(ax, countries, rakiura, grat_segments)

    pad = _EARTH_RADIUS * 0.02 # 2% breathing room so the boundary ring isn't flush with the figure edge
    ax.set_xlim(-_EARTH_RADIUS - pad, _EARTH_RADIUS + pad)
    ax.set_ylim(-_EARTH_RADIUS - pad, _EARTH_RADIUS + pad)

    return fig


def make_globe_map() -> Figure:
    """fetch data and render the full annotated globe; thin wrapper for backwards compatibility"""
    return render_globe(fetch_globe_data())


def make_globe_map_clean() -> Figure:
    """fetch data and render the clean opening globe; thin wrapper for backwards compatibility"""
    return render_globe_clean(fetch_globe_data())
