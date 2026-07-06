"""
Natural Earth physical data fetching via the naciscdn CDN -- no API key required, no bundled data.
Called only by `common.load_nz_outline()` which handles its own write-once cache; this module does no caching of its own"""

import geopandas as gpd
from shapely.geometry import box

_NE_BASE = "https://naciscdn.org/naturalearth/10m/physical"

# bounding box (WGS84) that covers NZ mainland + Stewart Island, nothing else.
_NZ_BBOX = box(165.0, -47.5, 178.5, -34.0)


def fetch_land_polygons(crs: str = "EPSG:4326") -> gpd.GeoDataFrame:
    """Fetch Natural Earth 10m land polygons for the whole world."""
    gdf = gpd.read_file(f"{_NE_BASE}/ne_10m_land.zip")
    if crs != "EPSG:4326":
        gdf = gdf.to_crs(crs)
    return gdf


def fetch_nz_outline(crs: str = "EPSG:4326") -> gpd.GeoDataFrame:
    """Fetch Natural Earth 10m land polygons clipped to New Zealand"""
    land = gpd.read_file(f"{_NE_BASE}/ne_10m_land.zip")
    nz = gpd.clip(land, _NZ_BBOX)
    if crs != "EPSG:4326":
        nz = nz.to_crs(crs)
    return nz
