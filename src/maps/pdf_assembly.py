"""
El ensamblador -- builds the five-page A4 PDF from the PNG files saved by the orchestrate module -- pages 1 and 5 are globe pages with 
heading and pepeha text; pages 2-4 embed one map PNG each with a pepeha line, subtitle, and source colophon below.
Called from orchestrate.py after all PNGs are saved to disk."""

import io
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages

from src.maps.styles import FONTS, PALETTE, SIZES

# NB: Te reo Māori characters use unicode escapes throughout (e.g. \u0101 = ā, \u014d = ō); avoids any encoding issues across editors and OSes

_MM = 1 / 25.4 # mm to inches conversion; no me gusta usar los unidades de Trump
A4_W, A4_H = 210 * _MM, 297 * _MM
PAGE_BG = PALETTE["ink"]


def _to_img(fig_src: plt.Figure, dpi: int = 250) -> np.ndarray: # dpi 250 is a good balance between quality and file size
    """render a matplotlib figure to a NumPy pixel array via an in-memory PNG buffer.
    Used to embed rendered map figures as images within the PDF assembly pages"""
    buf = io.BytesIO() # in-memory file buffer -- avoids writing a temporary PNG to disk
    fig_src.savefig(buf, format="png", dpi=dpi, facecolor=fig_src.get_facecolor())
    buf.seek(0) # rewind to the start of the buffer so plt.imread() reads from the beginning
    return plt.imread(buf)


def _colophon(fig: plt.Figure, crs_line: str, sources_line: str = "") -> None:
    """place a two-line bottom-right colophon at 5 mm page margins"""
    text = crs_line if not sources_line else f"{crs_line}\n{sources_line}"
    fig.text(
        0.976, 0.017, text, # ~5 mm from the bottom-right corner
        ha="right", va="bottom",
        color=PALETTE["platinum"], fontsize=SIZES["scalebar"],
        fontfamily=FONTS["sans"],
        multialignment="right",
    )


def _make_map_page(
    fig_map: plt.Figure | np.ndarray, # accepts either a Figure (converts via _to_img) or an already-loaded numpy array
    pepeha_line: str,
    colophon: tuple,
    subtitle: str = "",
) -> plt.Figure:
    """Compose one A4 map page: map upper ~70%, pepeha line + subtitle below.

    Used for pages 2-4 only. Pages 1 and 5 (globes) are built inline in
    assemble_pdf because their text layouts differ too much from this
    template -- page 1 has a heading and course attribution, page 5 has
    four pepeha pairs"""
    img = _to_img(fig_map) if isinstance(fig_map, plt.Figure) else fig_map # normalise input to numpy array
    fig = plt.figure(figsize=(A4_W, A4_H))
    fig.patch.set_facecolor(PAGE_BG)
    ax_m = fig.add_axes([0.04, 0.30, 0.92, 0.67]) # [left, bottom, width, height] as figure fractions -- map occupies upper ~70% of page
    ax_m.imshow(img, aspect="auto")
    ax_m.axis("off")
    # text block below the map: pepeha line, italic subtitle 0.024 below, then colophon at the page margin
    fig.text(
        0.5, 0.23, pepeha_line,
        ha="center", va="center",
        color=PALETTE["platinum"], fontsize=SIZES["pepeha"],
        fontfamily=FONTS["serif"],
    )
    if subtitle:
        fig.text(
            0.5, 0.206, subtitle,
            ha="center", va="center",
            color=PALETTE["platinum"], fontsize=SIZES["tick"],
            fontfamily=FONTS["sans"], fontstyle="italic",
        )
    _colophon(fig, colophon[0], colophon[1] if len(colophon) > 1 else "")
    return fig


def assemble_pdf(png_paths: dict[str, Path], out_path: Path) -> None:
    """read map PNGs from disk, build all 5 A4 pages, and write the PDF"""
    img_globe_clean = plt.imread(str(png_paths["globe_clean"]))
    img_maunga      = plt.imread(str(png_paths["maunga"]))
    img_awa         = plt.imread(str(png_paths["awa"]))
    img_iwi         = plt.imread(str(png_paths["iwi"]))
    img_globe       = plt.imread(str(png_paths["globe_annotated"]))

    figs = []

    # ---------------------------------------------------------------------------
    # Page 1 -- Opening globe
    # ---------------------------------------------------------------------------
    fig_p1 = plt.figure(figsize=(A4_W, A4_H))
    fig_p1.patch.set_facecolor(PAGE_BG)
    # globe pages use a slightly smaller axes box than map pages -- more text needs to fit below
    ax_g0 = fig_p1.add_axes([0.04, 0.32, 0.92, 0.65])
    ax_g0.imshow(img_globe_clean, aspect="auto")
    ax_g0.axis("off")
    fig_p1.text(
    # vertical rhythm: heading + translation tight pair, course attribution further below
        0.5, 0.270, "Kia ora t\u0101tou",
        ha="center", va="center",
        color=PALETTE["platinum"], fontsize=SIZES["heading"],
        fontfamily=FONTS["serif"],
    )
    fig_p1.text(
        0.5, 0.246, "Greetings all",
        ha="center", va="center",
        color=PALETTE["platinum"], fontsize=SIZES["tick"],
        fontfamily=FONTS["sans"], fontstyle="italic",
    )
    fig_p1.text(
        0.5, 0.19, "GISC401 | Mapped Pepeha | 2026 | Z.Hynd",
        ha="center", va="center",
        color=PALETTE["platinum"], fontsize=SIZES["label_lg"],
        fontfamily=FONTS["sans"],
    )
    _colophon(
        fig_p1,
        "Orthographic projection, centred 43.5\u00b0S / 172.6\u00b0E",
        "Sources: Natural Earth 110m, 10m",
    )
    figs.append(fig_p1)

    # ---------------------------------------------------------------------------
    # Pages 2-4 -- Map pages
    # ---------------------------------------------------------------------------
    figs.append(_make_map_page(
        img_maunga,
        "Ko Tapuae-O-Uenuku te maunga",
        colophon=("NZTM2000 (EPSG:2193)", "Sources: Copernicus GLO-90 DEM, LINZ"),
        subtitle="Tapuae‑o‑Uenuku (‘the footprint of Uenuku’, the rainbow atua) is the mountain",
    ))
    figs.append(_make_map_page(
        img_awa,
        "Ko Wairau te awa",
        colophon=(
            "NZTM2000 (EPSG:2193)",
            "Sources: Copernicus GLO-90 DEM, LINZ, Natural Earth 10m (inset)",
        ),
        subtitle="Wairau is the river",
    ))
    figs.append(_make_map_page(
        img_iwi,
        "Ko Rongowhakaata te iwi",
        colophon=(
            "NZTM2000 (EPSG:2193)",
            "Sources: Copernicus GLO-90 DEM, LINZ, Gisborne District Council, Natural Earth 10m (inset)",
        ),
        subtitle="Rongowhakaata is the iwi",
    ))

    # ---------------------------------------------------------------------------
    # Page 5 -- Closing globe
    # ---------------------------------------------------------------------------
    fig_p5 = plt.figure(figsize=(A4_W, A4_H))
    fig_p5.patch.set_facecolor(PAGE_BG)
    ax_g5 = fig_p5.add_axes([0.04, 0.32, 0.92, 0.65])
    ax_g5.imshow(img_globe, aspect="auto")
    ax_g5.axis("off")
    # vertical rhythm: each pepeha line paired with italic translation 0.024 below; pairs spaced ~0.041 down the page
    fig_p5.text(
        0.5, 0.275, "N\u014d Te Waipounamu ahau",
        ha="center", va="center", color=PALETTE["platinum"], fontsize=SIZES["pepeha"],
        fontfamily=FONTS["serif"],
    )
    fig_p5.text(
        0.5, 0.251, "I am from the South Island",
        ha="center", va="center", color=PALETTE["platinum"], fontsize=SIZES["tick"],
        fontfamily=FONTS["sans"], fontstyle="italic",
    )
    fig_p5.text(
        0.5, 0.210, "He akonga ahau ki te Whare W\u0101nanga o Waitaha",
        ha="center", va="center", color=PALETTE["platinum"], fontsize=SIZES["pepeha"],
        fontfamily=FONTS["serif"],
    )
    fig_p5.text(
        0.5, 0.186, "I am a student at the University of Canterbury",
        ha="center", va="center", color=PALETTE["platinum"], fontsize=SIZES["tick"],
        fontfamily=FONTS["sans"], fontstyle="italic",
    )
    fig_p5.text(
        0.5, 0.145, "Ko Zak t\u014dku ingoa",
        ha="center", va="center", color=PALETTE["platinum"], fontsize=SIZES["pepeha"],
        fontfamily=FONTS["serif"],
    )
    fig_p5.text(
        0.5, 0.121, "My name is Zak",
        ha="center", va="center", color=PALETTE["platinum"], fontsize=SIZES["tick"],
        fontfamily=FONTS["sans"], fontstyle="italic",
    )
    fig_p5.text(
        0.5, 0.080, "T\u0113n\u0101 t\u0101tou katoa",
        ha="center", va="center", color=PALETTE["platinum"], fontsize=SIZES["pepeha"],
        fontfamily=FONTS["serif"],
    )
    fig_p5.text(
        0.5, 0.056, "Greetings to us all",
        ha="center", va="center", color=PALETTE["platinum"], fontsize=SIZES["tick"],
        fontfamily=FONTS["sans"], fontstyle="italic",
    )
    _colophon(
        fig_p5,
        "Orthographic projection, centred 43.5\u00b0S / 172.6\u00b0E",
        "Sources: Natural Earth 110m, 10m",
    )
    figs.append(fig_p5)

    # ---------------------------------------------------------------------------
    # Write PDF
    # ---------------------------------------------------------------------------
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(out_path) as pdf:
        for fig in figs:
            pdf.savefig(fig, facecolor=fig.get_facecolor())
            plt.close(fig)
