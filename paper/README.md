# Paper: Quran-Nazm: Reducing Layout Variance in Quran Typesetting

LaTeX sources of the article introducing Quran-Nazm, in the ACM template (`acmart`, `sigconf`): the full-paper version, 9 pages including references. The planned 4- and 10-page versions are described in [`VERSIONS.md`](VERSIONS.md). The earlier IEEE version is commit `04bd8fe`.

| File | Content |
|---|---|
| `main.tex` | the article |
| `refs.bib` | bibliography (BibTeX, `ACM-Reference-Format` style) |
| `acmart.cls`, `ACM-Reference-Format.bst` | the ACM class and bibliography style (TeX Live 2023 copies, LPPL), bundled so the paper builds anywhere |
| `make_figures.py` | rebuilds every figure from the repository data |
| `figures/` | charts (vector PDF), Nazm pages (vector PDF, cut from `output/quran-nazm.pdf`) and Madina print crops (PNG) |
| `main.pdf` | the compiled paper |

## Version

The paper's version is set by `\paperversion` near the top of `main.tex` (currently v0.1.0) and printed as a footnote to the title. Bump it on each revision.

## Build

```bash
make            # pdflatex, bibtex, pdflatex, pdflatex
```

Requirements: pdfLaTeX with the `libertine`, `newtx` and `inconsolata` packages (ACM's fonts; all in a full TeX Live), plus `booktabs`, `subcaption` and `tikz`. Arabic appears only inside figures. The charts are set in Linux Libertine to match the text; all fonts are embedded.

For submission, change the class options from `[sigconf,nonacm]` to `[sigconf,review,anonymous]` if the call asks for double-blind review, and fill in the conference metadata ACM provides.

## Rebuilding the figures

```bash
make figures    # or: python3 make_figures.py
```

`make_figures.py` reads `data/*.json`, `figures/*.png` and `output/quran-nazm.pdf` from the repository root. The page-156 natural-length figure also shapes text, so it needs the quran-madina-html checkout and the fonts prepared by `scripts/00_prepare.py` (see `docs/RENDERING.md`). `data/nazm_line_stretch.json` (per-line stretch of the render) is written by `python scripts/65_nazm_line_stretch.py`.
