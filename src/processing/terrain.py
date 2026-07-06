"""
Hillshade generation from elevation arrays -- a single thin wrapper around `matplotlib.colors.LightSource`.
Kept as its own module so the greyscale-hillshade parameters (azimuth, altitude, vertical exaggeration) 
live in one place; used by `awa.py` and `iwi.py`. `maunga.py` doesn't call this -- it uses `LightSource.shade()` 
directly because it needs full RGBA output."""

import numpy as np
from matplotlib.colors import LightSource


def compute_hillshade(data: np.ndarray, dx_m: float = 30.0) -> np.ndarray:
    """Compute a normalised hillshade array from a 2D elevation array (metres)
   
    Light source at azimuth 315° / altitude 45° -- the standard cartographic NW-mid-angle convention. 
    `vert_exag=1.5` is mild exaggeration; `dx_m` should match the DEM's pixel size in metres (90 for GLO-90, 30 for GLO-30).
    """
    ls = LightSource(azdeg=315, altdeg=45)
    return ls.hillshade(data, vert_exag=1.5, dx=dx_m, dy=dx_m)
