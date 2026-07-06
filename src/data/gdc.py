"""
GDC ArcGIS fetching -- the Rongowhakaata statutory acknowledgement polygon for the iwi map.
No API key needed; results cached as a GeoPackage on first fetch"""

from pathlib import Path
import requests
import geopandas as gpd

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

# ArcGIS FeatureServer -- no key needed for public open data
GDC_RONGOWHAKAATA_URL = "https://services7.arcgis.com/8G10QCd84QpdcTJ9/ArcGIS/rest/services/statutory_acknowledgements/FeatureServer/6"

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_GDC_CACHE_DIR = _PROJECT_ROOT / "local_resources" / "gdc"


# ---------------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------------

def fetch_arcgis_feature_layer(url: str, crs: str = "EPSG:2193") -> gpd.GeoDataFrame:
    """Fetch all features from an ArcGIS FeatureServer layer endpoint"""
    params = {
        "where": "1=1",           # return all features
        "outFields": "*",
        "f": "geojson",
        "outSR": "2193",          # request NZTM2000 directly
    }
    r = requests.get(f"{url}/query", params=params)
    r.raise_for_status()
    return gpd.read_file(r.text)


def fetch_rongowhakaata_aoi() -> gpd.GeoDataFrame:
    """Fetch the Rongowhakaata statutory acknowledgement polygon from GDC ArcGIS.
   
    Returns the raw multipart feature -- "Rongo AOI", "Pecked", and "Coastal Marine Area" parts.
    Filtering and clipping happen in iwi.py
    """
    cache_path = _GDC_CACHE_DIR / "rohe.gpkg"
    if cache_path.exists():
        return gpd.read_file(cache_path)

    result = fetch_arcgis_feature_layer(GDC_RONGOWHAKAATA_URL)

    _GDC_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    result.to_file(cache_path, driver="GPKG")

    return result
