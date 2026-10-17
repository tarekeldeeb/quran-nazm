"""Madina 1441H vs Quran-Nazm with 10 pages per hizb vs Quran-Nazm with 20 pages per juz.

    python scripts/69_unit_comparison.py        # writes data/unit_comparison.json

All three are measured the same way, on juz 1-29 (juz 30 is an exception in each):
the stretch of a line is the line width over its natural width, shaped unstretched
in the DigitalKhatt font (Madina: the print's own lines, data/m_1441H.json, full
lines only; Nazm: the renderer's layout, lines over 1.8x are centred and left out).

The spread of log stretch is split, in squares, into between-juz, between pages of
a juz and within a page; the between-hizb part is reported separately. These do
not depend on the line width (a common factor on every line). The type size and
the median stretch do: Nazm sets the width from its compression limit (25% for the
hizb design, 19% for the juz design, both giving type at 93% of the print); the juz
layout is also shown at the print's own type size.
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import DATA, QMH

import render_mushaf as R

txt = R.Text()
HZ, JZ = R.hizb_ranges(), R.juz_ranges()


def unit_of(ayah, ranges):
    i = txt.flat.index(ayah) + 1
    return next(k + 1 for k, (a0, a1) in enumerate(ranges) if a0 <= i < a1)


def madina_pages():
    """[(juz, hizb, [stretch of each full line])] per page, from the print."""
    db = json.load(open(os.path.join(QMH, "assets", "db", "v2", "Madina-1441H.json")))
    first = {}
    for s, sura in enumerate(db["suras"], 1):
        for a, aya in enumerate(sura["ayas"][2:], 1):  # two decoration slots precede the ayahs
            if (s, a) in txt.flat_set:
                first.setdefault(aya["p"], (s, a))
    lines = json.load(open(os.path.join(DATA, "m_1441H.json")))
    pages = {}
    for o in lines:
        if o["full"]:
            pages.setdefault(o["p"], []).append(1 / o["ratio"])
    out, cur = [], None
    for p in range(1, len(db["lines"]) + 1):
        cur = first.get(p, cur)
        out.append((unit_of(cur, JZ), unit_of(cur, HZ), pages.get(p, [])))
    return out, [unit_of(first[p], HZ) for p in sorted(first)], first


def nazm_pages(unit, shrink):
    book, W, _ = R.build_layout(txt, shrink, unit)
    out = []
    for p in book:
        s = [W / r[2] for r in p["rows"] if r[0] == "text"]
        out.append((unit_of(p["ayahs"][0], JZ), unit_of(p["ayahs"][0], HZ), [x for x in s if x <= 1.8]))
    return out, W, book


def metrics(pages, W=None, scale=1.0):
    body = [(j, h, [x * scale for x in s]) for j, h, s in pages if j <= 29 and s]
    ls = np.array([math.log(x) for _, _, s in body for x in s])
    jm = {j: np.mean([math.log(x) for jj, _, s in body if jj == j for x in s]) for j in range(1, 30)}
    hm = {}
    for _, h, s in body:
        hm.setdefault(h, []).extend(math.log(x) for x in s)
    pm = [np.mean(np.log(s)) for _, _, s in body]
    between_juz = math.sqrt(np.mean([(jm[j] - ls.mean()) ** 2 for j, _, s in body for _ in s]))
    between_pages = math.sqrt(np.mean([(m - jm[j]) ** 2 for (j, _, s), m in zip(body, pm) for _ in s]))
    within = math.sqrt(np.mean([(math.log(x) - m) ** 2 for (_, _, s), m in zip(body, pm) for x in s]))
    s = np.exp(ls)
    spread = [np.std(np.log(q)) for _, _, q in body if len(q) >= 10]
    fill = [float(np.mean(q)) for _, _, q in body]
    return dict(lines=int(len(ls)), stretch_median=float(np.median(s)), stretch_p5=float(np.percentile(s, 5)),
                stretch_p95=float(np.percentile(s, 95)), lines_off_10pct=float((np.abs(ls) > math.log(1.1)).mean()),
                lines_compressed_10pct=float((s < 1 / 1.1).mean()), lines_compressed_25pct=float((s < 0.75).mean() + 0),
                sd_log_stretch=float(ls.std()), sd_between_juz=between_juz,
                sd_between_hizbs=float(np.std([np.mean(v) for v in hm.values() if v])),
                sd_between_pages_in_juz=between_pages, sd_within_page=within,
                within_page_spread_median=float(np.median(spread)),
                neighbour_page_diff_median=float(np.median(np.abs(np.diff(pm)))),
                sparsest_page=max(fill), densest_page=min(fill))


def alignment(book):
    """Hizbs and juz that start on the first line of a page (title rows count as the start)."""
    starts_h = {a0 for a0, _ in HZ}
    starts_j = {a0 for a0, _ in JZ}
    top = [txt.flat.index(p["ayahs"][0]) + 1 for p in book]
    return dict(hizbs_at_page_top=sum(1 for a in starts_h if a in top),
                juz_at_page_top=sum(1 for a in starts_j if a in top))


def main():
    txt.flat_set = set(txt.flat)
    res = {}
    mp, mad_page_hizb, first = madina_pages()
    res["madina_1441h"] = dict(type_size=1.0, pages=len(mp), **metrics(mp))
    top = {txt.flat.index(a) + 1 for a in first.values()}
    res["madina_1441h"].update(hizbs_at_page_top=sum(1 for a0, _ in HZ if a0 in top),
                               juz_at_page_top=sum(1 for a0, _ in JZ if a0 in top))
    # each layout at its own compression limit: 25% for the hizb design, 19% (the default) for
    # the juz design; both then give type at 93% of the print
    for unit, shrink in (("hizb", 0.25), ("juz", 0.19)):
        pages, W, book = nazm_pages(unit, shrink)
        res[f"nazm_{unit}"] = dict(type_size=15437.6 / W, compression_limit=shrink,
                                   pages=len(book), **metrics(pages), **alignment(book))
        if unit == "juz":  # the same juz layout at the print's type size (25% limit)
            res["nazm_juz_at_print_type_size"] = dict(type_size=1.0, **metrics(pages, scale=15437.6 / W))
    json.dump(res, open(os.path.join(DATA, "unit_comparison.json"), "w"), indent=1)
    keys = list(res["nazm_hizb"].keys())
    print(f"{'':32s}" + "".join(f"{k[:14]:>16s}" for k in res))
    for k in keys:
        print(f"{k:32s}" + "".join(f"{res[c].get(k, float('nan')):>16.3f}" if isinstance(res[c].get(k), float)
                                    else f"{str(res[c].get(k, '')):>16s}" for c in res))


if __name__ == "__main__":
    main()
