# Data

| File | Content | Made by |
|---|---|---|
| `hafs-rub-start-ayahs.json` | global ayah index (1–6236) where each of the 240 rub' starts, with a leading 0 and a closing 6237 | `HizbQuarterList` from the [quran-meta](https://www.npmjs.com/package/quran-meta) package, Hafs lists (MIT) |
| `m_1441H.json`, `m_1405H.json` | every line of the Madina layouts: page, line, text, natural width in the DigitalKhatt font, ratio to the line width, words, letters | `scripts/10_measure_natural_widths.py` |
| `w_1441H.json` | pen width, ink and line box for each line of the 1441H scan | `scripts/20_measure_pen_weight.py` |
| `mg.json` | ayah markers found at line starts on the scan, compared with the layout data | `scripts/30_ayah_markers_and_gaps.py` |
| `rub_minmax.json` | per rub': text length, surah starts, minimal 30-line width | `scripts/40_rub_minmax.py` |
| `sweep2.json` | the shrink-limit comparison (10–45%) | `scripts/64_shrink_sweep_squeeze.py` |
| `hist60.json` | natural length of the 60 hizbs, in Madina pages | hizb histogram in `docs/hizb-layout-study.html` |

Widths are in font units of the QMH New Madina font (1000 per em); the 1441H line width is 15,437.6 units.
