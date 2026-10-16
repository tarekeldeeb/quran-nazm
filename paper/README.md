# Paper: Quran-Nazm, rule-based typesetting of the Madina Mushaf

LaTeX sources of the article introducing Quran-Nazm (two columns, A4, six pages).

| File | Content |
|---|---|
| `main.tex` | the article |
| `refs.bib` | bibliography (BibTeX, `plainnat`) |
| `make_figures.py` | rebuilds every figure from the repository data |
| `figures/` | charts (vector PDF), Nazm pages (vector PDF, cut from `output/quran-nazm.pdf`) and Madina print crops (PNG) |
| `main.pdf` | the compiled paper |

## Build

```bash
make            # xelatex, bibtex, xelatex, xelatex
```

Requirements: XeLaTeX with `fontspec`, `natbib`, `booktabs`, `tikz`, `subcaption`, `titlesec` and the TeX Gyre fonts (Pagella, Heros, Cursor). Arabic appears only inside figures, so no Arabic LaTeX packages are needed.

## Rebuilding the figures

```bash
make figures    # or: python3 make_figures.py
```

`make_figures.py` reads `data/*.json`, `figures/*.png` and `output/quran-nazm.pdf` from the repository root. The page-156 natural-length figure also shapes text, so it needs the quran-madina-html checkout and the fonts prepared by `scripts/00_prepare.py` (see `docs/RENDERING.md`). `data/nazm_line_stretch.json` (per-line stretch of the render) is written by `python scripts/65_nazm_line_stretch.py`.
