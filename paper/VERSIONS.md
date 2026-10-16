# Two versions of the paper: 4 and 10 pages

**Status (October 2026):** `main.tex` is now the full-paper version, 9 pages including references, with about one page kept free for the reader study and the re-measurement on the King Fahd Complex vector masters. Section order: introduction, related work, the root variance of the reading units, how the Madina print absorbs it, design, implementation, evaluation with ablations, reproducibility, limitations. The 4-page version is not built; derive it from `main.tex` only if needed.

The current `main.tex` is a 6-page ACM `sigconf` paper. DocEng accepts **full papers up to 10 pages** and **short papers up to 4 pages** (plus 2-page demonstration abstracts), all in the ACM format. Whether references count toward those limits is not stated in the parts of the call we read; plan for references *inside* the limit until the 2027 call says otherwise.

The same work cannot go to both tracks of the same DocEng. The two versions serve different moments:

| | 4-page short paper | 10-page full paper |
|---|---|---|
| Purpose | Fallback if the full paper is not ready by the full-paper deadline; also a ready version for a workshop or a TUG talk | The main DocEng submission |
| Message | One problem, one method, one result | The problem measured in depth, the design space, the system, and an evaluation with ablations |
| Status of the evidence | Uses what exists today | Needs the high-resolution masters re-measured and, ideally, a reader study |
| DocEng track and deadline (2026 pattern) | Short papers, mid-June | Full papers, early May (abstract two weeks before) |

## Current 6 pages, by section

Estimated from the compiled PDF (ACM `sigconf`, figures included):

| Section | Pages | Content |
|---|---|---|
| Title, abstract, teaser (Fig. 1) | 1.0 | Print vs Nazm, page 156 |
| 1 Introduction | 0.4 | Context, contributions |
| 2 Problem | 1.6 | Line density (Fig. 2, 3, Table 1), pen weight (Fig. 4 crops, Fig. 5), ayah markers |
| 3 Analysis and approach | 1.0 | Unit of consistency (Table 2, Fig. 6), page and line cutting (Eq. 1), compression limit (Table 3) |
| 4 Implementation | 1.1 | Pages (Fig. 7), pipeline (Fig. 8), five paragraphs |
| 5 Results | 0.8 | Table 4, Fig. 9, the cost of the constraint |
| 6–7 Discussion, conclusion, acknowledgements | 0.4 | |
| References | 0.4 | 16 entries |

## 4-page version: what stays, what goes

The test for every element: does a reader need it to believe *"manual setting varies; Nazm's rules reduce the variance within a page by 38%"*?

| Element | Decision | Pages |
|---|---|---|
| Title, abstract (shortened to ~120 words), teaser Fig. 1 | Keep: the teaser is the whole argument in one picture | 0.9 |
| Introduction | Cut to one paragraph plus three contribution bullets | 0.25 |
| Line density: Fig. 3 histogram + two sentences | Keep | 0.35 |
| Page 156 at natural length (Fig. 2) | Drop: the teaser shows the same page | 0 |
| Table 1 (all print measurements) | Keep, condensed to 5 rows: it carries pen weight and markers too | 0.2 |
| Pen weight: crops figure | Keep one panel only, page 102 lines 4–5 (column width) | 0.2 |
| Fig. 5 weight-vs-crowding chart, ayah-marker crop | Drop, keep the numbers in text | 0 |
| Unit of consistency (Table 2, Fig. 6) | One sentence: "hizb lengths vary by 1.35×; ten pages per hizb is the smallest unit that stays within graceful stretch" | 0.1 |
| Page and line cutting, Eq. 1 | Keep: this is the method | 0.4 |
| Compression limit table (Table 3) | One sentence and the chosen value | 0.1 |
| Implementation | One paragraph; drop pipeline Fig. 8 and pages Fig. 7 | 0.25 |
| Results: Table 4 (6 rows) and Fig. 9 | Keep both | 0.6 |
| Limitations and conclusion | One paragraph | 0.2 |
| References | Trim to ~10: DigitalKhatt and Anane, Knuth–Plass, Mittelbach's pagination framework, KFGQPC, the scan or vector masters, quran-madina-html, HarfBuzz, Tanzil, Quran-Nazm | 0.35 |
| **Total** | | **≈ 4.0** |

A 4-page version is tight but realistic with today's material. Its weakness is the one a reviewer will name first: the print measurements rest on a 100 ppi scan. Swapping the crops and pen-weight numbers for the King Fahd Complex vector masters fixes that without adding space.

## 10-page version: what to add

Four pages of new material on top of today's six. In order of value to reviewers:

| Addition | Status | Pages |
|---|---|---|
| **Related work** section: Arabic justification (Benatia et al., Haralambous, Anane; a recent calligraphy-based justification scheme in *Computers in Human Behavior*), line breaking and pagination (Knuth–Plass; Plass's optimal pagination thesis; Mittelbach's *Framework for Globally Optimized Pagination*, DocEng 2016; Hurst, Li and Marriott's *Review of automatic document formatting*, DocEng 2009), and Quran typesetting (AlQalam, DigitalKhatt, KFGQPC fonts, quran-madina-html) | New writing; all references to be verified before use | 0.8 |
| **Print measurements on the vector masters**: redo pen weight and ink per letter on all 604 Illustrator pages; add the page-level drift chart (already in `docs/madina-variance-evidence.html`) | Needs `1441-AI-hafs.zip`; scripts exist | 0.6 |
| **Ablations**, mostly data we already have: rub', half hizb, hizb, juz (Table 2); 8 vs 10 pages per hizb; independent vs joint cuts (3.40× → 2.16×, 0.057 → 0.039); shrink limits 10–45% (Table 3); juz 30 at 24/25/26 pages and the sparsity cap | Recompute 8-vs-10 with the final method; the rest exists | 0.9 |
| **Reader study**: 20–30 readers (Quran teachers, calligraphers, regular readers) rank paired print and Nazm pages without knowing which is which, for evenness, legibility and beauty | New; needs participants and, depending on institution, ethics approval | 0.8 |
| **Implementation details**: juz 30 page scoring, the raster ink check, the shared-glyph PDF writer, run time and file size | Text exists in `docs/RENDERING.md` | 0.4 |
| **Extremes and failure cases**: densest page (horizontal squeeze), sparsest page, juz 30 splits, with a per-hizb stretch chart | Figures exist in `docs/hizb-layout-study.html` | 0.5 |

The full version also gives room to keep Fig. 2 (page 156 at natural length) and Fig. 8 (pipeline), which the 4-page version drops.

## Suggested order of work

1. **Now**: keep `main.tex` (6 pages) as the master text; it already contains everything the 4-page version needs.
2. **When the vector masters arrive**: re-measure, replace the crops and pen-weight numbers in the master.
3. **January–March**: write related work, run the ablations and, if possible, the reader study, growing the master toward 10 pages.
4. **April**: if the full paper is on track, submit it; derive the 4-page version only if it is needed as a fallback for the short-paper deadline in June.

Deriving the short version from the full one is easy; growing a short paper into a full one tends to produce a padded paper. So the 10-page version should lead.
