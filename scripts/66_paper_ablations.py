"""Ablations of the Quran-Nazm layout for the full paper (hizbs 1-58).

    python scripts/66_paper_ablations.py        # writes data/ablations.json

Variants, each with its own common line width (longest natural line - 25%):
  final         10 pages per hizb; page cuts and line cuts chosen jointly (the renderer)
  pages8        8 pages per hizb, otherwise as final
  greedy_pages  each page cut at the ayah end nearest to its share, lines as final
  greedy_both   greedy page cuts and each line cut at the word nearest to its share
  no_penalty    final without the penalty for splitting a surah that fits on one page

Metrics follow the paper: stretch s = W / natural width of a line; the spread
inside a page is the standard deviation of log s over its lines (median over
pages); lines needing more than 1.8x are centred by the renderer and left out.
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import DATA

import render_mushaf as R

LW_MADINA = 15437.6
SHRINK = 0.25


def greedy_pages(txt, ayahs, pages):
    w = [sum(x for _, x in txt.units(s, a)) + txt.sp * len(txt.units(s, a)) for s, a in ayahs]
    hdr = [R.header_lines(s) if a == 1 else 0 for s, a in ayahs]
    q = sum(w) / (pages * R.LINES - sum(hdr))
    v = np.concatenate([[0], np.cumsum(np.array(w) + np.array(hdr) * q)])
    cuts = [0]
    for k in range(1, pages):
        t = k * v[-1] / pages
        cand = [i for i in range(cuts[-1] + 1, len(ayahs) - (pages - k) + 1)]
        cuts.append(min(cand, key=lambda i: abs(v[i] - t)))
    cuts.append(len(ayahs))
    return [ayahs[a:b] for a, b in zip(cuts[:-1], cuts[1:])]


def greedy_lines(ws, n, sp):
    m = len(ws)
    n = max(1, min(n, m))
    cum = np.concatenate([[0], np.cumsum(np.array(ws) + sp)])
    cuts = [0]
    for j in range(1, n):
        t = j * cum[-1] / n
        cand = range(cuts[-1] + 1, m - (n - j) + 1)
        cuts.append(min(cand, key=lambda b: abs(cum[b] - t)))
    cuts.append(m)
    return list(zip(cuts[:-1], cuts[1:]))


def layout(txt, pages, page_fn):
    book = []
    for h, (a0, a1) in enumerate(R.hizb_ranges()[:58]):
        for pa in page_fn(txt, txt.flat[a0 - 1:a1 - 1], pages):
            book.append(dict(hizb=h + 1, ayahs=pa, rows=R.page_rows(txt, pa)))
    return book


def metrics(txt, book, squeeze=True):
    nat = [[r[2] for r in p["rows"] if r[0] == "text"] for p in book]
    W = max(max(n) for n in nat) * (1 - SHRINK)
    pages = [[W / x for x in n] for n in nat]
    s = np.array([x for p in pages for x in p if x <= 1.8])
    spread = [np.std(np.log([x for x in p if x <= 1.8])) for p in pages if len([x for x in p if x <= 1.8]) >= 2]
    page_mean = [np.mean(p) for p in pages]
    split = 0
    for i in range(1, len(book)):
        prev, cur = book[i - 1]["ayahs"][-1], book[i]["ayahs"][0]
        if prev[0] == cur[0] and book[i - 1]["hizb"] == book[i]["hizb"]:
            n_ayas = len(txt.suras[cur[0] - 1]["ayas"])
            ws = [x for a in range(1, n_ayas + 1) for _, x in txt.units(cur[0], a)]
            if R.header_lines(cur[0]) + R.lines_needed(ws, W, txt.sp) <= R.LINES:
                split += 1
    out = dict(pages=len(book), type_size=LW_MADINA / W, stretch_median=float(np.median(s)),
               stretch_p5=float(np.percentile(s, 5)), stretch_p95=float(np.percentile(s, 95)),
               stretch_max=float(max(x for p in pages for x in p)),
               within_page_spread=float(np.median(spread)),
               sparsest_page=float(max(page_mean)), densest_page=float(min(page_mean)),
               compressed_over_10=float((s < 0.9).mean()), short_surah_splits=split,
               words_per_line=float(np.mean([len(r[1]) for p in book for r in p["rows"] if r[0] == "text"])))
    if squeeze:
        xs = []
        for p in book:
            for r in p["rows"]:
                if r[0] == "text" and r[2] > W:
                    xs.append(R.justify(txt.font, " ".join(r[1]), W).x_scale)
        n_lines = sum(1 for p in book for r in p["rows"] if r[0] == "text")
        out["lines_squeezed"] = sum(1 for x in xs if x < 0.999) / n_lines
        out["squeeze_max"] = 1 - min(xs) if xs else 0.0
    return out


def main():
    txt = R.Text()
    res = {}
    res["final"] = metrics(txt, layout(txt, 10, R.fixed_pages))
    res["pages8"] = metrics(txt, layout(txt, 8, R.fixed_pages))
    res["greedy_pages"] = metrics(txt, layout(txt, 10, greedy_pages))
    joint = R.opt_lines
    R.opt_lines = greedy_lines
    res["greedy_both"] = metrics(txt, layout(txt, 10, greedy_pages))
    R.opt_lines = joint
    pen = R.SMALL_SURA_PENALTY
    R.SMALL_SURA_PENALTY = 0.0
    res["no_penalty"] = metrics(txt, layout(txt, 10, R.fixed_pages))
    R.SMALL_SURA_PENALTY = pen
    # per-hizb mean log stretch for the final layout (between-hizb variance)
    book = layout(txt, 10, R.fixed_pages)
    nat = [[r[2] for r in p["rows"] if r[0] == "text"] for p in book]
    W = max(max(n) for n in nat) * (1 - SHRINK)
    per_hizb = {}
    for p, n in zip(book, nat):
        per_hizb.setdefault(p["hizb"], []).extend(math.log(W / x) for x in n if W / x <= 1.8)
    res["per_hizb_mean_stretch"] = [math.exp(np.mean(per_hizb[h])) for h in sorted(per_hizb)]
    res["between_hizb_sd"] = float(np.std([np.mean(per_hizb[h]) for h in per_hizb]))
    page_means = [float(np.mean([W / x for x in n])) for n in nat]
    res["sparsest_page_number"] = int(np.argmax(page_means)) + 1
    res["densest_page_number"] = int(np.argmin(page_means)) + 1
    json.dump(res, open(os.path.join(DATA, "ablations.json"), "w"), indent=1)
    for k, v in res.items():
        if isinstance(v, dict):
            print(k, {a: round(b, 3) if isinstance(b, float) else b for a, b in v.items()})
    print("between-hizb sd", round(res["between_hizb_sd"], 3), "sparsest page", res["sparsest_page_number"],
          "densest page", res["densest_page_number"])


if __name__ == "__main__":
    main()
