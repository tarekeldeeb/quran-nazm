# Generating the Quran-Nazm PDF

This guide rebuilds `output/quran-nazm.pdf` from scratch. A full run takes about one minute on a laptop.

## 1. What you need

| Requirement | Why |
|---|---|
| Python 3.10 or newer | runs the scripts |
| `pip install uharfbuzz fonttools brotli numpy freetype-py pymupdf` | text shaping, font reading (WOFF2 needs `brotli`; quran-madina-html's justifier needs `freetype-py`; `pymupdf` places the frame and header art) |
| A checkout of [quran-madina-html](https://github.com/tarekeldeeb/quran-madina-html) on its `v2.0` branch | provides the 1441H text and line data, the patched DigitalKhatt New Madina font, Amiri Quran, and the HarfBuzz justifier (`src/db/v2/justify.py`) |

The analysis scripts that measure the printed Mushaf also need `opencv-python-headless` and `scikit-image`, plus the King Fahd Complex PDF. The renderer does not.

## 2. Set up

```bash
git clone https://github.com/tarekeldeeb/quran-nazm.git
git clone -b v2.0 https://github.com/tarekeldeeb/quran-madina-html.git
cd quran-nazm
pip install uharfbuzz fonttools brotli numpy freetype-py pymupdf
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
| `quran-nazm.pdf` | the Mushaf: a cover and 604 pages, 145 × 210 mm, vector outlines, one bookmark per surah, right-to-left page order |
| `quran-nazm-report.json` | type size, stretch and compression statistics, and the rule checks |
| `quran-nazm-layout.json` | every page: hizb, first and last ayah, and the words on each line |
| `quran-nazm-summary.txt` | a short statistics summary beside the Madina print's values (also printed at the end of the run): type size, stretch, the spread of line stretch split into between juz, between pages and within a page, squeezed lines, alignment, extremes and the rule checks |

Options:

```bash
python scripts/render_mushaf.py --shrink 0.25                     # a different compression limit (default 0.19)
python scripts/render_mushaf.py --no-cover                        # no cover page
python scripts/render_mushaf.py --art none                        # Quran-Nazm's own frame and headers
python scripts/render_mushaf.py --unit hizb                       # 10 pages per hizb instead of 20 per juz
python scripts/render_mushaf.py --pages 1-20 --out build/sample.pdf   # draw only some pages
```

The layout is always computed for the whole book, because the common line width depends on every hizb; `--pages` only limits what is drawn.

## 5. How a page is made

1. **Text.** The Hafs text of the 1441H Madina print comes from the quran-madina-html database. Each ayah marker is glued to the word before it, so no line can begin with a marker.
2. **Juz boundaries.** `data/hafs-rub-start-ayahs.json` lists where each rub' starts (from the `quran-meta` package, MIT). Every eighth rub' starts a juz, every fourth a hizb; hizbs only label the running heads.
3. **One line per juz.** Each word is shaped with HarfBuzz in the DigitalKhatt font with no stretching, and the juz is treated as one long line. Surah headers count as the lines they occupy: two (title and basmala), or one for Al-Fatiha, whose basmala is its first ayah, and for Al-Tawba, which has none.
4. **Twenty pages.** Nineteen page cuts are placed at ayah ends, all chosen together by dynamic programming so every page carries as close to a twentieth of the juz as the ayahs allow, measured in shaped text width. Every page therefore ends with an ayah number. (`--unit hizb` instead cuts each hizb into 10 pages.)
5. **Fifteen lines.** On each page, every surah starts on a new line under its header, and no surah title may start below line 11 (`TITLE_MAX_ROW`): a page cut that would put a title lower is not allowed, so the search moves the surah to the top of the next page instead. The remaining lines are shared among the page's surah segments so that none is crowded, and each segment is cut into lines at word boundaries, all cuts chosen together to make the lines as equal as possible.
6. **One line width.** After juz 1–29 are laid out, the longest natural line in the book is found. The common line width is that length reduced by the shrink limit (19%, `--shrink`), so no line ever needs more than 19% compression. This sets the type size: 93% of the Madina 1441H print (100% with `--shrink 0.25`, at the cost of squeezing nearly half the lines; `--unit hizb` gives 93% at 25%).
7. **Justification.** Each line is justified to the common width. Short lines stretch letters (kashida and alternates) and spaces with the DigitalKhatt rules ported in quran-madina-html v2. Long lines tighten their spaces to at most 60% and are then scaled horizontally; the font's word-shrink features (`shr1`, `shrr`) are not used, because inside a full line they push words into each other. The few lines that would need more than 1.8× stretch (a handful of words left before a surah ends on a page) are centred instead.
8. **Juz 30.** The one exception, on 24 pages (`JUZ30_PAGES_AS_JUZ`); 20 pages cannot hold its 37 surahs under the title rule. (With `--unit hizb`, hizb 59 keeps 10 pages and hizb 60 takes 14, `JUZ30_PAGES`.) With 37 surahs in juz 30, each starting on a new line under its header, text length is a poor guide to how full a page is, so every candidate page is scored by the lines it really needs at the common width: its average stretch should be close to 1, and it may never need more than the shrink limit. Where up to three short surahs share a page, the lines are also shared so that every title stays at line 11 or higher (each surah still gets the lines it needs within the shrink limit). No page may be sparser than 1.35× average stretch (`JUZ30_MAX_STRETCH`), except the last page: under the title rule, surahs 112–114 cannot fill it more than 1.50×, and a fourth surah would push a title to line 12; a split surah keeps at least two ayahs on each page (`MIN_SPLIT_AYAHS`), and a cut inside a surah that would fit on one page costs far more than any imbalance, so short surahs stay whole wherever these rules allow. Both hizbs of juz 30 are cut this way, each on its own page count. Change `JUZ30_PAGES` in the script for other counts; hizb 60 needs at least 13 pages within the rules.
9. **Collision check.** Every set line is checked for ink contact between neighbouring words: glyph boxes that intersect are rasterised and compared pixel by pixel. Where two words touch (usually a small pause mark under the tall stroke of a following kaf), only that space is widened, in small steps, and the line is rescaled to its width.
10. **Page frame and surah headers.** By default (`--art hafs-adi`) every page is framed by the Hafs al-'Adi ornament and each surah header uses the matching cartouche, both vector art from [quran-assets](https://github.com/quran-ws/quran-assets), kept in `assets/art/hafs-adi/`. Each SVG has a transparent slot: the frame's slot is stretched over the text block, and the header's slot holds the surah name, set in the same DigitalKhatt font and shrunk if needed to fit. The art is laid under the text after the PDF is written, each SVG stored once as a form object. This art is CC BY-NC-SA 4.0 (provisional); `--art none` uses Quran-Nazm's own vector frame and headers instead. Running heads and page numbers use Amiri Quran, whose digits read well at small sizes.
11. **PDF.** Every glyph outline is written once as a PDF form object and placed on each page by position, which keeps the 604-page file near 11 MB with sharp vector text at any zoom. A static cover (a short Arabic and English description, opening "مصحف نظم", and credits, inside the page frame) precedes page 1; the file opens two pages at a time with its first page on the left, so a two-page viewer shows the cover on the left and page 1 on the right, and page labels keep "1" on the Mushaf's first page. `--no-cover` leaves the cover out and keeps right-to-left page order.

## 6. Checks

The report confirms the rules on every page: `every_page_ends_on_ayah` and `no_line_starts_with_marker` must both be `true`, `lowest_surah_title_row` must be at most 11, and `word_collisions` must be `0` (`collisions_cleared_by_spacing` counts the lines the spacing step fixed). It also records how many lines needed a horizontal squeeze (`lines_squeezed`), the one visible compromise at a 25% limit, and lists any surah short enough for one page that still spans two (`short_suras_split`); see `docs/findings.md`.

## 7. Reproducing the research

The numbered scripts in `scripts/` reproduce the analysis behind these rules, in order (10–12 line density, 20–22 pen weight, 30–31 ayah markers, 40–44 rub' and hizb sizing, 50–53 ayah-bounded pages, 60–64 the single-line method and shrink limits, 66 the hizb-design ablations, 67 the surah-title rule, 68 the exact joint optimum, 69 Madina vs 10-page hizb vs 20-page juz, 70 the juz-design studies, 71 letter counts of the juz under classical counting conventions; 68 and 70 need `pip install numba highspy`). They write intermediates to `build/`. Scripts 20–31 need the King Fahd Complex PDF and `python scripts/00_prepare.py` to extract its page images.
