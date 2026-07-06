"""
Vector processing -- general utilities (reprojection, bbox clipping) plus Wairau river preparation for the awa map.
Used by the maps modules to turn raw fetched vectors into plot-ready layers."""

import geopandas as gpd
from shapely.geometry import box


def reproject(gdf: gpd.GeoDataFrame, epsg: int) -> gpd.GeoDataFrame:
    """Reproject a GeoDataFrame to the given EPSG code"""
    return gdf.to_crs(epsg=epsg)


def clip_to_bbox(gdf: gpd.GeoDataFrame, bbox: list[float]) -> gpd.GeoDataFrame:
    """Clip a GeoDataFrame to a bounding box [minx, miny, maxx, maxy] in the GDF's own CRS"""
    minx, miny, maxx, maxy = bbox
    return gpd.clip(gdf, box(minx, miny, maxx, maxy))


def prepare_rivers(
    lines: gpd.GeoDataFrame,
    polys: gpd.GeoDataFrame,
    main_stem_name: str = "Wairau River",
    simplify_tolerance: float = 150.0,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Turn raw LINZ river data (centrelines + polygons) into four plot-ready layers for the awa map.
    
    LINZ supplies named rivers as two separate layers -- centrelines (layer-103632) and polygons 
    (layer-103631) -- and each named river is broken into many fragments. This function combines them 
    into the four layers the awa render expects: main stem centreline, tributary centrelines, main stem 
    polygon boundary, and tributary polygon boundaries. Each is dissolved (one geometry per named river) 
    and simplified to keep render time and file size sensible.

    Parameters
    ----------
    lines : GeoDataFrame of river centrelines (layer-103632), in EPSG:2193.
        Must have a 'name_ascii' column.
    polys : GeoDataFrame of river polygons (layer-103631), in EPSG:2193.
        Must have a 'name_ascii' column.
    main_stem_name : name_ascii value identifying the main stem.
    simplify_tolerance : simplification tolerance in metres. Default 150 m is invisible at
        this scale; drops vertex count enough to keep render time sensible.

    Returns
    -------
    (stem_lines, trib_lines, stem_boundaries, trib_boundaries)

    stem_lines : main stem centrelines, dissolved into one geometry
    trib_lines : tributary centrelines, dissolved by name
    stem_boundaries : polygon boundaries for main stem, dissolved
    trib_boundaries : polygon boundaries for tributaries, dissolved by name
    All four are simplified to simplify_tolerance metres.
    """
    def _dissolve_simplify(gdf: gpd.GeoDataFrame, by: str | None) -> gpd.GeoDataFrame:
        """Dissolve by column (or fully if by=None) and simplify"""
        if gdf.empty:
            return gdf
        if by is not None:
            result = gdf.dissolve(by=by).reset_index()
        else:
            result = gdf.dissolve().reset_index()
        result.geometry = result.geometry.simplify(simplify_tolerance)
        return result

    # split lines into stem and tributaries
    stem_lines_raw = lines[lines["name_ascii"] == main_stem_name].copy()
    trib_lines_raw = lines[lines["name_ascii"] != main_stem_name].copy()

    stem_lines = _dissolve_simplify(stem_lines_raw, by=None)
    trib_lines = _dissolve_simplify(trib_lines_raw, by="name_ascii")

    # extract polygon boundaries
    if not polys.empty:
        polys_with_boundary = polys.copy()
        polys_with_boundary.geometry = polys.geometry.boundary

        stem_polys = polys_with_boundary[
            polys_with_boundary["name_ascii"] == main_stem_name
        ].copy()
        trib_polys = polys_with_boundary[
            polys_with_boundary["name_ascii"] != main_stem_name
        ].copy()

        stem_boundaries = _dissolve_simplify(stem_polys, by=None)
        trib_boundaries = _dissolve_simplify(trib_polys, by="name_ascii")
    else:
        stem_boundaries = gpd.GeoDataFrame(columns=["geometry"], crs=lines.crs)
        trib_boundaries = gpd.GeoDataFrame(columns=["geometry"], crs=lines.crs)

    return stem_lines, trib_lines, stem_boundaries, trib_boundaries
