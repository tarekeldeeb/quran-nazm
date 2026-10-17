# Paper: Quran-Nazm: Reducing Layout Variance in Quran Typesetting

LaTeX sources of the article introducing Quran-Nazm, in the ACM template (`acmart`, `sigconf`): the full-paper version, 11 pages including references. The planned 4- and 10-page versions are described in [`VERSIONS.md`](VERSIONS.md). The earlier IEEE version is commit `04bd8fe`.

| File | Content |
|---|---|
| `main.tex` | the article |
| `refs.bib` | bibliography (BibTeX, `ACM-Reference-Format` style) |
| `acmart.cls`, `ACM-Reference-Format.bst` | the ACM class and bibliography style (TeX Live 2023 copies, LPPL), bundled so the paper builds anywhere |
| `make_figures.py` | rebuilds every figure from the repository data |
| `figures/` | charts (vector PDF), Nazm pages (vector PDF, cut from `output/quran-nazm.pdf`) and Madina print crops (PNG) |
| `main.pdf` | the compiled paper |

## Version

The paper's version is set by `\paperversion` near the top of `main.tex` (currently v0.3.1) and printed as a footnote to the title. Bump it on each revision.

| Version | Changes |
|---|---|
| v0.3.1 | Review comments: teaser shows both text blocks in the same Hafs frame at the same size (the print's page 156 placed in the frame by `make_figures.py`) and is smaller, so the abstract fits on page 1; the ayah count in Section 5.2 is now $N$ (Table 1 uses $n$ for rub' per unit); the planned blind reader study is replaced by review from the scholars of the Mushaf review committees; future work adds the other narrations, up to all twenty of the ten readings. |
| v0.3.0 | New design: every juz on exactly 20 pages (juz 30 on 24) instead of every hizb on 10; compression limit 19%; no surah title below line 11; the font's shrinking features never used. New: the unit question reframed in Section 3; title rule and compression analysis in Design; parameters table, cover and statistics summary in Implementation; three-way comparison Madina vs 10 pages per hizb vs 20 pages per juz (Table 6, Fig. 12); juz-design ablations, exact optimum checked with HiGHS, per-juz stretch, title-rule cost and juz 30 variants in Evaluation. Hizbs at a page top in the print corrected to 38 (was 43, which counted the first three lines). 11 pages including references. |
| v0.2.0 | Nazm pages use the Hafs al-'Adi page frame and surah headers of quran-assets (CC BY-NC-SA 4.0), so the teaser compares the two text blocks inside the same frame; Output paragraph, captions, Limitations (Design), conclusion and acknowledgements updated; quran-assets cited. Results unchanged. |
| v0.1.0 | First ACM full-paper version: root variance of the reading units (Section 3), Giza affiliation, Measurement limitation removed. |

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
