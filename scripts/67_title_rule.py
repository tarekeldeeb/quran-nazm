"""Cost of the surah-title rule: no surah title below line 11 of a page.

    python scripts/67_title_rule.py        # writes data/title_rule.json

Compares the layout with the rule (the renderer's default) against the layout
without it (and juz 30's earlier sparsity cap of 1.35). Hizbs 1-58 obey the rule
through their page cuts alone; in juz 30, where up to three short surahs share a
page, the lines of a page are also shared so that each title stays at line 11 or
higher. The last page (surahs 112-114, as in the print) cannot be fuller than
1.50x under the rule, so it is exempt from juz 30's 1.35 sparsity cap.

A third variant, `whole_surah_exempt`, lets a title sit lower only when its surah
also ends on that page (it never continues onto the next page).

Metrics follow the paper: stretch s = W / natural width of a line; lines over
1.8x are centred by the renderer and left out of the spread; a page's fill is
the mean stretch of its lines.
"""
import collections
import importlib
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import DATA, QMH

import render_mushaf as R

SHRINK = 0.25
LW_MADINA = 15437.6


def title_rows(book):
    return [i + 1 for p in book for i, r in enumerate(p["rows"]) if r[0] == "title"]


def page_stats(book, W):
    out = []
    for p in book:
        s = [W / r[2] for r in p["rows"] if r[0] == "text"]
        k = [x for x in s if x <= 1.8]
        out.append(dict(fill=float(np.mean(s)), spread=float(np.std(np.log(k))) if len(k) >= 2 else None,
                        lines=s))
    return out


def short_splits(txt, book, W):
    span = {}
    for i, p in enumerate(book):
        for s, a in p["ayahs"]:
            span.setdefault(s, set()).add(i)
    out = []
    for s, pg in span.items():
        if len(pg) > 1:
            ws = [x for a in range(1, len(txt.suras[s - 1]["ayas"]) + 1) for _, x in txt.units(s, a)]
            if R.header_lines(s) + R.lines_needed(ws, W, txt.sp) <= R.LINES:
                out.append(s)
    return sorted(out)


def build(txt, rule, exempt=False):
    R.TITLE_RULE, R.TITLE_RULE_EXEMPT_WHOLE = rule, exempt
    book, W, _ = R.build_layout(txt, SHRINK)
    return book, W


def summary(txt, book, W, ps, sel):
    pages = [ps[i] for i in sel]
    s = np.array([x for p in pages for x in p["lines"] if x <= 1.8])
    allx = np.array([x for p in pages for x in p["lines"]])
    sp = [p["spread"] for p in pages if p["spread"] is not None]
    return dict(pages=len(sel), stretch_median=float(np.median(s)), stretch_p95=float(np.percentile(s, 95)),
                stretch_max=float(allx.max()), lines_over_1_5=int((allx > 1.5).sum()),
                lines_centred=int((allx > 1.8).sum()), within_page_spread=float(np.median(sp)),
                fill_min=float(min(p["fill"] for p in pages)), fill_max=float(max(p["fill"] for p in pages)))


def main():
    txt = R.Text()
    res = {}
    books = {}
    for name, rule, ex in (("without_rule", False, False), ("with_rule", True, False),
                           ("whole_surah_exempt", True, True)):
        book, W = build(txt, rule, ex)
        books[name] = (book, W)
        ps = page_stats(book, W)
        h58 = [i for i, p in enumerate(book) if p["hizb"] <= 58]
        j30 = [i for i, p in enumerate(book) if p["hizb"] >= 59]
        rows = title_rows(book)
        res[name] = dict(type_size=LW_MADINA / W, pages=len(book),
                         titles_below_11=sum(1 for r in rows if r > 11),
                         title_row_histogram=dict(sorted(collections.Counter(rows).items())),
                         hizbs_1_58=summary(txt, book, W, ps, h58), juz30=summary(txt, book, W, ps, j30),
                         short_suras_split=short_splits(txt, book, W),
                         low_titles=[dict(page=i + 1, surah=r[1], row=k + 1) for i, p in enumerate(book)
                                     for k, r in enumerate(p["rows"]) if r[0] == "title" and k + 1 > 11])
    (b0, W0), (b1, W1) = books["without_rule"], books["with_rule"]
    ps0, ps1 = page_stats(b0, W0), page_stats(b1, W1)
    changed = [i for i in range(len(b0)) if b0[i]["ayahs"] != b1[i]["ayahs"]]
    res["changed_pages"] = [dict(page=i + 1, hizb=b1[i]["hizb"],
                                 before=[b0[i]["ayahs"][0], b0[i]["ayahs"][-1]],
                                 after=[b1[i]["ayahs"][0], b1[i]["ayahs"][-1]],
                                 fill_before=round(ps0[i]["fill"], 3), fill_after=round(ps1[i]["fill"], 3))
                            for i in changed]
    res["hizbs_changed"] = sorted({b1[i]["hizb"] for i in changed})
    # page fill relative to its hizb: how far the rule pushes a page from an equal share
    dev = {}
    for name, (b, W), ps in (("without_rule", books["without_rule"], ps0), ("with_rule", books["with_rule"], ps1)):
        d = []
        for i, p in enumerate(b):
            if p["hizb"] <= 58:
                h = [ps[j]["fill"] for j, q in enumerate(b) if q["hizb"] == p["hizb"]]
                d.append(abs(math.log(ps[i]["fill"] / np.mean(h))))
        dev[name] = dict(median=float(np.median(d)), p95=float(np.percentile(d, 95)), max=float(max(d)))
    res["page_fill_deviation_from_hizb_mean"] = dev
    # the Madina print, for reference
    d = json.load(open(os.path.join(QMH, "assets", "db", "v2", "Madina-1441H.json")))
    mad = [(p, i) for p, page in enumerate(d["lines"], 1) for i, l in enumerate(page, 1) if l["k"] == "sura"]
    res["madina_1441h"] = dict(titles_below_11=[dict(page=p, row=i) for p, i in mad if i > 11],
                               title_row_histogram=dict(sorted(collections.Counter(i for _, i in mad).items())))
    R.TITLE_RULE, R.TITLE_RULE_EXEMPT_WHOLE = True, False
    json.dump(res, open(os.path.join(DATA, "title_rule.json"), "w"), indent=1, ensure_ascii=False)
    for name in ("without_rule", "with_rule", "whole_surah_exempt"):
        r = res[name]
        print(name, "type", round(r["type_size"], 3), "titles below 11:", r["titles_below_11"],
              "splits", r["short_suras_split"])
        for part in ("hizbs_1_58", "juz30"):
            print("  ", part, {k: round(v, 3) if isinstance(v, float) else v for k, v in r[part].items()})
    print("pages changed", len(changed), "in hizbs", res["hizbs_changed"])
    for c in res["changed_pages"]:
        if c["hizb"] <= 58:
            print("  ", c)
    print("page fill deviation", {k: {a: round(b, 3) for a, b in v.items()} for k, v in dev.items()})
    print("Madina titles below line 11:", res["madina_1441h"]["titles_below_11"])


if __name__ == "__main__":
    main()
