# Generating the Quran-Nazm PDF

This guide rebuilds `output/quran-nazm.pdf` from scratch. A full run takes about one minute on a laptop.

## 1. What you need

| Requirement | Why |
|---|---|
| Python 3.10 or newer | runs the scripts |
| `pip install uharfbuzz fonttools brotli numpy` | text shaping, font reading (WOFF2 needs `brotli`) |
| A checkout of [quran-madina-html](https://github.com/tarekeldeeb/quran-madina-html) on its `v2.0` branch | provides the 1441H text and line data, the patched DigitalKhatt New Madina font, Amiri Quran, and the HarfBuzz justifier (`src/db/v2/justify.py`) |

Only the analysis scripts that measure the printed Mushaf also need `pymupdf`, `opencv-python-headless` and `scikit-image`, plus the King Fahd Complex PDF. The renderer does not.

## 2. Set up

```bash
git clone https://github.com/tarekeldeeb/quran-nazm.git
git clone -b v2.0 https://github.com/tarekeldeeb/quran-madina-html.git
cd quran-nazm
pip install uharfbuzz fonttools brotli numpy
```

The scripts find their inputs through three environment variables (see `scripts/paths.py`):

| Variable | Default | Meaning |
|---|---|---|
| `QMH` | `../quran-madina-html` | the quran-madina-html checkout |
| `NAZM_WORK` | `build/` | folder for fonts and generated files |
| `SCAN_PDF` | `quran-madina.pdf` | King Fahd Complex PDF (analysis only) |

With the two repositories side by side as above, the defaults work and nothing needs to be set.

## 3. Prepare the fonts (once)

```bash
python scripts/00_prepare.py
```

This writes `build/madina.otf` (QMH New Madina, the DigitalKhatt font used for the text), `build/oldmadina.otf` and `build/amiri.ttf` (Amiri Quran, used only for page numbers and running heads).

## 4. Render

```bash
python scripts/render_mushaf.py
```

Output, in `build/`:

| File | Content |
|---|---|
| `quran-nazm.pdf` | the Mushaf: 604 pages, 145 × 210 mm, vector outlines, one bookmark per surah, right-to-left page order |
| `quran-nazm-report.json` | type size, stretch and compression statistics, and the rule checks |
| `quran-nazm-layout.json` | every page: hizb, first and last ayah, and the words on each line |

Options:

```bash
python scripts/render_mushaf.py --shrink 0.20                     # a different compression limit
python scripts/render_mushaf.py --pages 1-20 --out build/sample.pdf   # draw only some pages
```

The layout is always computed for the whole book, because the common line width depends on every hizb; `--pages` only limits what is drawn.

## 5. How a page is made

1. **Text.** The Hafs text of the 1441H Madina print comes from the quran-madina-html database. Each ayah marker is glued to the word before it, so no line can begin with a marker.
2. **Hizb boundaries.** `data/hafs-rub-start-ayahs.json` lists where each rub' starts (from the `quran-meta` package, MIT). Every fourth rub' starts a hizb.
3. **One line per hizb.** Each word is shaped with HarfBuzz in the DigitalKhatt font with no stretching, and the hizb is treated as one long line. Surah headers count as the lines they occupy: two (title and basmala), or one for Al-Fatiha, whose basmala is its first ayah, and for Al-Tawba, which has none.
4. **Ten pages.** Nine page cuts are placed at ayah ends, all chosen together by dynamic programming so every page carries as close to a tenth of the hizb as the ayahs allow. Every page therefore ends with an ayah number.
5. **Fifteen lines.** On each page, every surah starts on a new line under its header. The remaining lines are shared among the page's surah segments so that none is crowded, and each segment is cut into lines at word boundaries, all cuts chosen together to make the lines as equal as possible.
6. **One line width.** After all hizbs 1–58 are laid out, the longest natural line in the book is found. The common line width is that length reduced by the shrink limit (25%), so no line ever needs more than 25% compression. This sets the type size: 93% of the Madina 1441H print.
7. **Justification.** Each line is justified to the common width with the DigitalKhatt rules ported in quran-madina-html v2: short lines stretch letters (kashida and alternates) and spaces; long lines tighten spaces, use the font's narrow forms, and only then scale horizontally. The few lines that would need more than 1.8× stretch (a handful of words left before a surah ends on a page) are centred instead.
8. **Juz 30.** Hizbs 59–60 are the declared exception and share exactly 24 pages. With 37 surahs, each starting on a new line under its header, text length is a poor guide to how full a page is, so every candidate page is scored by the lines it really needs at the common width: its average stretch should be close to 1, and it may never need more than the shrink limit. A cut inside a surah that would fit on one page costs far more than any imbalance, so short surahs stay whole wherever the 24 pages allow. Change `JUZ30_PAGES` in the script for another count.
9. **Surah headers.** Each header is vector art drawn directly in the PDF: a pale ribbon between two fine rules, a cartouche with pointed ends and a double outline holding the surah name (set in the same DigitalKhatt font), a diamond on each side and an eight-pointed star at each end. Running heads and page numbers use Amiri Quran, whose digits read well at small sizes.
10. **PDF.** Every glyph outline is written once as a PDF form object and placed on each page by position, which keeps the 604-page file near 10 MB with sharp vector text at any zoom.

## 6. Checks

The report confirms two rules on every page: `every_page_ends_on_ayah` and `no_line_starts_with_marker` must both be `true`. It also records how many lines needed a horizontal squeeze (`lines_squeezed`), the one visible compromise at a 25% limit, and lists any surah short enough for one page that still spans two (`short_suras_split`); see `docs/findings.md`.

## 7. Reproducing the research

The numbered scripts in `scripts/` reproduce the analysis behind these rules, in order (10–12 line density, 20–22 pen weight, 30–31 ayah markers, 40–44 rub' and hizb sizing, 50–53 ayah-bounded pages, 60–64 the single-line method and shrink limits). They write intermediates to `build/`. Scripts 20–31 need the King Fahd Complex PDF and `python scripts/00_prepare.py` to extract its page images.
