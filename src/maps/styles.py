"""
Style Centralisation. Intended to be the single source of visual truth for the project: colour palette (inferno-derived),
fonts, type sizes, figure dimensions, and inset geometry. Plus apply_theme() for matplotlib rcParams and style_map_axes() 
for per-axes tick and spine styling.

Imported by orchestrate.py at session start (apply_theme) and by every module in src/maps/ for the constants and style_map_axes().
"""

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.ticker import MaxNLocator, AutoMinorLocator, ScalarFormatter

# ---------------------------------------------------------------------------
# Figure geometry -- A4 portrait, map panel in mm converted to matplotlib inches
# ---------------------------------------------------------------------------

_MM = 25.4  # mm per inch, for converting dimensions to matplotlib's inches units (no me gustan los unidades de Trump)

# all maps use this figsize so pages are consistent in the PDF
# 170 mm wide × 185 mm  -- exact aspect chosen during early dev, cannot remember why; works visually, leaving as-is
FIGSIZE = (170 / _MM, 185 / _MM)
# square aspect because the globe is circular... por supuesto
GLOBE_FIGSIZE = (170 / _MM, 170 / _MM)

# inset rectangle [left, bottom, width, height] as figure fractions
# bottom-right corner, same position on every map that has an inset; tuned to fit beneath the map panel without overlap
INSET_RECT = [0.63, 0.04, 0.24, 0.30]

# maunga colormap
MAUNGA_CMAP_NAME = "inferno"
MAUNGA_CMAP_LO   = 0.2 # clamp the low end of the inferno ramp -- avoids near-black at the coast
MAUNGA_CMAP_HI   = 0.9 # clamp the high end of the inferno ramp -- avoids near-white at the peaks

# globe graticule rendering parameters:
GLOBE_GRATICULE_STEP   = 10 # plot a graticule every 10° of latitude and longitude
GLOBE_GRATICULE_SAMPLE = 0.5 # sample every 0.5° for smooth-ish curves

# graticule label positions:
# positioned to frame NZ
# latitude labels are plotted where graticules cross this meridian (degrees)
GLOBE_LAT_LABEL_LON = 135.0
# longitude labels are plotted where graticules cross this parallel (degrees)
GLOBE_LON_LABEL_LAT = -15.0

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

PALETTE = {
    "ink":        "#07051b",   # inferno 0.05 -- page, space, furniture
    "water":      "#160b39",   # inferno 0.10 -- ocean, rivers, lakes
    "wananga":    "#6a176e",   # inferno 0.30 -- Te Whare Wānanga o Waitaha marker
    "waipounamu": "#bc3754",   # inferno 0.50 -- Te Waipounamu on globe
    "iwi":        "#dd513a",   # inferno 0.60 -- rohe polygon
    "awa":        "#f98e09",   # inferno 0.75 -- river highlight/glow
    "maunga":     "#f6d746",   # inferno 0.90 -- peak accent
    "land":       "#82a3a1",   # Coolors.co   -- neutral landmass on globe/insets
    "platinum":   "#edf2ef",   # Coolors.co   -- labels, ticks, spines, furniture
}

# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------

FONTS = {
    "sans":  "DejaVu Sans",    # axes labels, scalebar, north arrow, tick labels, colophons
    "serif": "DejaVu Serif",   # geographic names, pepeha text
}

# pt sizes tuned to A4 page scale; relative ordering matters more than absolutes
SIZES = {
    "scalebar": 6,
    "tick":     7,
    "label_sm": 8,
    "label_md": 9,
    "label_lg": 11,
    "title":    13,
    "pepeha":   20,
    "heading":  26,
}

# ---------------------------------------------------------------------------
# rcParams -- call once from main.ipynb before building any map
# ---------------------------------------------------------------------------

def apply_theme() -> None:
    """Set matplotlib rcParams for the whole notebook session.

    Call once before creating any figure -- rcParams only apply to figures
    built after they're set
    """
    plt.rcParams.update({
        "font.family":      FONTS["sans"],
        "axes.titlesize":   SIZES["title"],
        "axes.labelsize":   SIZES["label_sm"],
        "xtick.labelsize":  SIZES["tick"],
        "ytick.labelsize":  SIZES["tick"],
        "figure.facecolor": PALETTE["ink"],
        "axes.facecolor":   PALETTE["ink"],
        "xtick.color":      PALETTE["platinum"],
        "ytick.color":      PALETTE["platinum"],
        "axes.edgecolor":   PALETTE["platinum"],
        "text.color":       PALETTE["platinum"],
    })

# ---------------------------------------------------------------------------
# Axis styling -- call at the end of each map function, after set_xlim/set_ylim
# ---------------------------------------------------------------------------

def style_map_axes(ax: Axes) -> None:
    """Apply tick formatting and label style to a finished NZTM map axes

    call this after set_xlim / set_ylim so the locators have the correct range
    - no scientific notation
    - Y tick labels rotated 90°
    - ~5 major ticks, ~10 minor ticks
    - all furniture in PALETTE["platinum"]
    """
    fmt = ScalarFormatter(useOffset=False)
    fmt.set_scientific(False)
    ax.xaxis.set_major_formatter(fmt)
    ax.yaxis.set_major_formatter(fmt)

    # tick density tuned for the A4 map panel: ~5 major ticks reads cleanly without crowding,
    # 2 minor ticks per major gives enough texture without visual noise
    ax.xaxis.set_major_locator(MaxNLocator(nbins=5, integer=True))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5, integer=True))

    ax.xaxis.set_minor_locator(AutoMinorLocator(2))
    ax.yaxis.set_minor_locator(AutoMinorLocator(2))

    _tl = PALETTE["platinum"]

    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(True)
        ax.spines[side].set_color(PALETTE["platinum"])
        ax.spines[side].set_linewidth(0.6) # thin but visible

    ax.tick_params(axis="both", colors=_tl)
    ax.tick_params(axis="y", labelrotation=90, labelsize=SIZES["tick"], labelcolor=_tl, pad=2) # smaller pad than x because the rotated label has less visual weight beside the tick
    ax.tick_params(axis="x", labelsize=SIZES["tick"], labelcolor=_tl, pad=3)
    ax.xaxis.label.set_color(_tl)
    ax.yaxis.label.set_color(_tl)
    
    # ticks on all four sides, labels only on bottom and left
    ax.tick_params(axis="x", which="both", top=True,
                   labeltop=False, colors=PALETTE["platinum"])
    ax.tick_params(axis="y", which="both", right=True,
                   labelright=False, colors=PALETTE["platinum"])

    # re-anchor the rotated y tick labels so the visual midpoint aligns with the tick mark, not the text origin.
    ax.figure.canvas.draw() # force a render pass so tick label objects exist before we adjust their alignment
    for lbl in ax.get_yticklabels():
        lbl.set_verticalalignment("center")