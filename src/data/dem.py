"""
Fetch Copernicus GLO-30 or GLO-90 DEM tiles from AWS S3 (public, no auth required) -- merged and clipped to a bbox.
Tiles are Cloud-Optimised GeoTIFFs, so only the pixels inside the bbox are downloaded; tile files cached in 
`local_resources/dem_tiles/` to avoid re-fetching. Used by all four map modules for hillshade and elevation rendering"""

import math
import os
import warnings
from pathlib import Path
import requests

# required to avoid a 301 redirect when fetching Copernicus DEM tiles from AWS S3
os.environ.setdefault("AWS_REGION", "eu-central-1")
import rioxarray  # noqa: F401 -- registers the .rio accessor on xarray
import xarray as xr
from rioxarray.merge import merge_arrays


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOCAL_RESOURCES = _PROJECT_ROOT / "local_resources"
_TILE_CACHE = _LOCAL_RESOURCES / "dem_tiles"

_RESOLUTION_CONFIG = {
    30: ("copernicus-dem-30m", "COG_10"),
    90: ("copernicus-dem-90m", "COG_30"),
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_tile_urls(bbox_wgs84: list[float], resolution: int = 90) -> list[str]:
    """build S3 COG URLs for Copernicus GLO-30 or GLO-90 tiles covering bbox_wgs84."""
    if resolution not in _RESOLUTION_CONFIG:
        raise ValueError(f"resolution must be 30 or 90, got {resolution!r}")
    bucket, prefix = _RESOLUTION_CONFIG[resolution]
    base = f"https://{bucket}.s3.eu-central-1.amazonaws.com"
    min_lon, min_lat, max_lon, max_lat = bbox_wgs84
    # Southern Hemisphere: tile S41 covers 41°S-42°S, so abs(max_lat) gives the
    # lowest tile number (northernmost) and abs(min_lat) gives the highest (southernmost).
    lat_start = math.floor(abs(max_lat))          # e.g. floor(41.1) = 41  (northernmost row)
    lat_end   = math.ceil(abs(min_lat))           # e.g. ceil(42.0)  = 42  (southernmost row)
    lon_start = math.floor(min_lon)               # e.g. floor(172.5) = 172
    lon_end   = math.ceil(max_lon - 1e-9)         # e.g. ceil(174.3 - ε) = 175; avoids
                                                  #   adding an extra tile when max_lon
                                                  #   falls exactly on an integer boundary
    urls = []
    # lat_end + 1: range() is exclusive of the upper bound, but we need the southernmost
    # tile row (lat_end) included.  S{lat} covers lat°S to (lat+1)°S, so both lat_start
    # and lat_end rows may contain data within the bbox.
    for lat in range(lat_start, lat_end + 1):
        for lon in range(lon_start, lon_end):
            name = f"Copernicus_DSM_{prefix}_S{lat:02d}_00_E{lon:03d}_00_DEM"
            urls.append(f"{base}/{name}/{name}.tif")
    return urls


def _get_tile(url: str) -> xr.DataArray | None:
    """Return a DataArray for one tile URL, using the local cache if available"""
    filename = url.split("/")[-1]
    local_path = _TILE_CACHE / filename
    if not local_path.exists():
        response = requests.get(url)
        if response.status_code != 200:
            # tile doesn't exist on S3 (expected for ocean areas).
            return None
        _TILE_CACHE.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(response.content)
    return rioxarray.open_rasterio(local_path, masked=True).squeeze("band", drop=True)
        #^^ masked=True turns nodata into NaN; squeeze drops the singleton band dim so callers get a 2D array


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_dem(bbox_wgs84: list[float], resolution: int = 90) -> xr.DataArray:
    """Fetch, merge, and clip Copernicus DEM tiles for `bbox_wgs84`

    resolution=90 (GLO-90) is the project default; 30 (GLO-30) is available but downloads roughly 9× 
    the data for a detail gain that doesn't show at the project's output scale

    Tiles missing from S3 are silently skipped with a warning -- expected for ocean-bounded bboxes where Copernicus has no coverage
    """
    urls = _get_tile_urls(bbox_wgs84, resolution)
    tiles = []
    for url in urls:
        da = _get_tile(url)
        if da is not None:
            tiles.append(da)

    if not tiles:
        raise RuntimeError(f"No DEM tiles found for bbox {bbox_wgs84}. Check coordinates.")

    if len(tiles) == 1:
        dem = tiles[0]
    else:
        dem = merge_arrays(tiles)

    min_lon, min_lat, max_lon, max_lat = bbox_wgs84
    dem = dem.rio.clip_box(minx=min_lon, miny=min_lat, maxx=max_lon, maxy=max_lat)

    if len(tiles) < len(urls):
        warnings.warn(
            f"fetch_dem: {len(urls) - len(tiles)} of {len(urls)} tiles were missing "
            "(expected for ocean areas).",
        )

    return dem
