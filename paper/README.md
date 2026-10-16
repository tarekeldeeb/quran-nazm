# Paper: Quran-Nazm: Rule-Based Quran Typesetting that Reduces the Layout Variance of the Madina Mushaf

LaTeX sources of the article introducing Quran-Nazm, in the IEEE conference template (IEEEtran, A4, six pages).

| File | Content |
|---|---|
| `main.tex` | the article |
| `refs.bib` | bibliography (BibTeX, `IEEEtran` style) |
| `IEEEtran.cls`, `IEEEtran.bst` | the IEEE class and bibliography style, v1.8b (LPPL), bundled so the paper builds anywhere |
| `make_figures.py` | rebuilds every figure from the repository data |
| `figures/` | charts (vector PDF), Nazm pages (vector PDF, cut from `output/quran-nazm.pdf`) and Madina print crops (PNG) |
| `main.pdf` | the compiled paper |

## Build

```bash
make            # xelatex, bibtex, xelatex, xelatex
```

Requirements: XeLaTeX with `fontspec`, `mathptmx`, `cite`, `booktabs`, `tikz`, `subfig` and the TeX Gyre fonts (Termes, Heros, Cursor). Text is set in TeX Gyre Termes, the Times face IEEE asks for; all fonts are embedded. Arabic appears only inside figures, so no Arabic LaTeX packages are needed.

## Rebuilding the figures

```bash
make figures    # or: python3 make_figures.py
```

`make_figures.py` reads `data/*.json`, `figures/*.png` and `output/quran-nazm.pdf` from the repository root. The page-156 natural-length figure also shapes text, so it needs the quran-madina-html checkout and the fonts prepared by `scripts/00_prepare.py` (see `docs/RENDERING.md`). `data/nazm_line_stretch.json` (per-line stretch of the render) is written by `python scripts/65_nazm_line_stretch.py`.
