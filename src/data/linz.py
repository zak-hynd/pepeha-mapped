"""
LINZ WFS fetching -- generic `fetch_layer()` plus the Wairau river fetcher.
First-port-of-call for all LINZ vector data; results are cached as GeoPackages on disk"""

import os
import warnings
from pathlib import Path
import requests
from io import BytesIO
import geopandas as gpd
from shapely.geometry import box as _box

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LINZ_CACHE_DIR = _PROJECT_ROOT / "local_resources" / "linz"


def _linz_wfs_url() -> str:
    """build the LINZ WFS URL from the key currently in the environment"""
    key = os.environ.get("LINZ_API_KEY", "")
    return f"https://data.linz.govt.nz/services;key={key}/wfs"

# ---------------------------------------------------------------------------
# Generic WFS fetcher
# ---------------------------------------------------------------------------

def fetch_layer(layer_id: str, crs: str = "EPSG:2193", bbox=None, bbox_crs: str = "EPSG:4326", max_features: int = 500, cql_filter: str | None = None) -> gpd.GeoDataFrame:
    """Fetch a LINZ WFS layer as a GeoDataFrame, with optional bbox and CQL filter

    Caches results as a GeoPackage in local_resources/linz/, keyed on layer_id alone. This is safe only 
    because each layer ID is currently called from one fixed call site -- if the same layer is ever fetched 
    with different parameters, the cache will return whichever version was fetched first.

    Warns if the result has exactly max_features rows, since that's a strong signal the response was truncated.

    Parameters
    ----------
    bbox_crs : CRS of the bbox coordinates as an EPSG string (default EPSG:4326).
                Must match the coordinate units passed in bbox.
                Use "EPSG:2193" when passing NZTM metre coordinates.
    """
    # return cached copy if available; cache key is layer_id only, which is
    # safe here because each layer ID maps to a single fixed call site.
    cache_path = _LINZ_CACHE_DIR / f"{layer_id}.gpkg"
    if cache_path.exists():
        return gpd.read_file(cache_path)

    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": layer_id,
        "outputFormat": "application/json",
        "srsName": crs,
        "count": max_features,
    }
    if bbox is not None:
        params["bbox"] = f"{','.join(str(c) for c in bbox)},{bbox_crs}"
    if cql_filter is not None:
        params["CQL_FILTER"] = cql_filter

    response = requests.get(_linz_wfs_url(), params=params)
    response.raise_for_status()
    result = gpd.read_file(BytesIO(response.content))

    if len(result) == max_features:
        warnings.warn(
            f"fetch_layer({layer_id!r}): result has exactly {max_features} features - "
            "response may be truncated. Increase max_features or tighten the bbox.",
        )

    _LINZ_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    result.to_file(cache_path, driver="GPKG")

    return result


# ---------------------------------------------------------------------------
# Wairau rivers
# ---------------------------------------------------------------------------

# all the larger Wairau tributaries; lagoon-feeders (Opaoa et al.) excluded as they're not part of the river proper
_WAIRAU_RIVER_NAMES_ASCII = [
    "Avon River",
    "Branch River",
    "Goulter River",
    "Hamilton River",
    "Leatham River",
    "Marchburn River",
    "Ohinemahuta River",
    "Rainbow River",
    "Spray River",
    "Tuamarina River",
    "Waihopai River",
    "Wairau Diversion",
    "Wairau River",
    "Waikakaho River",
    "Wye River",
]

# bbox covering the full Wairau catchment in NZTM2000 (2 km pad)
_WAIRAU_BBOX = [1_575_000, 5_330_000, 1_684_000, 5_426_000]

# bbox (WGS84) enclosing the small Branch River; a tributary of the Taylor and Opaoa rivers
# There are two Branch Rivers in Marlborough; one isn't a 'true' tributary of the Wairau and can be excluded by bbox
_BRANCH_EXCL_BBOX_4326 = (173.8224115, -41.65756773, 173.9588105, -41.59186394)


def fetch_wairau_rivers() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Fetch Wairau catchment river lines and polygons

    Fetches layer-103632 (lines) and layer-103631 (polygons) over the
    full catchment bbox, then filters to named tributaries in Python
    using the name_ascii field.

    max_features=50000 is required for lines to avoid truncation -
    confirmed by testing that the full named set needs ~28000 raw features.

    Returns
    -------
    (lines, polygons) - both GeoDataFrames in EPSG:2193.
    """
    lines_raw = fetch_layer(
        "layer-103632",
        crs="EPSG:2193",
        bbox=_WAIRAU_BBOX,
        bbox_crs="EPSG:2193",
        max_features=50000,
    )
    polys_raw = fetch_layer(
        "layer-103631",
        crs="EPSG:2193",
        bbox=_WAIRAU_BBOX,
        bbox_crs="EPSG:2193",
        max_features=500, # river polygons are far fewer than centrelines; default cap is plenty
    )

    if not lines_raw.empty and "name_ascii" in lines_raw.columns:
        lines = lines_raw[
            lines_raw["name_ascii"].isin(_WAIRAU_RIVER_NAMES_ASCII)
        ].copy()
    else:
        lines = lines_raw

    # exclude the small Branch River -- the other Branch River has no features in this bbox
    _excl_geom = (
        gpd.GeoDataFrame(geometry=[_box(*_BRANCH_EXCL_BBOX_4326)], crs="EPSG:4326")
        .to_crs("EPSG:2193")
        .geometry.iloc[0]
    )
    branch_mask = (lines["name_ascii"] == "Branch River") & lines.intersects(_excl_geom)
    lines = lines[~branch_mask].copy()

    if not polys_raw.empty and "name_ascii" in polys_raw.columns:
        polys = polys_raw[
            polys_raw["name_ascii"].isin(_WAIRAU_RIVER_NAMES_ASCII)
        ].copy()
    else:
        polys = polys_raw

    return lines, polys
