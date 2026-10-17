"""Design studies of the 20-pages-per-juz layout, for the paper.

    python scripts/70_juz_design.py        # writes data/juz_design.json (about 10 minutes)

All on juz 1-29 unless stated; stretch s = W / natural width of a line; spread is the
standard deviation of log s (lines over 1.8x are centred and left out).

  compression   the compression limit sigma: type size, stretch and squeezed lines
  ablations     joint (DP) page and line cuts against greedy ones, each with its own W
  title_rule    what the rule "no surah title below line 11" changes
  optimum       the exact joint optimum (joint_layout.py) against the two-stage method
  juz30         juz 30 on 24 pages under different rules
  per_juz       mean stretch of every juz in the final layout
"""
import importlib
import json
import math
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import DATA

import joint_layout as J
import render_mushaf as R

SIGMA = 0.19
LW = 15437.6
txt = R.Text()
JUZ = [txt.flat[a0 - 1:a1 - 1] for a0, a1 in R.juz_ranges()]
A66 = importlib.import_module("66_paper_ablations")


def body(page_fn=R.fixed_pages, title_rule=True):
    book = []
    for j, ay in enumerate(JUZ[:29]):
        cuts = page_fn(txt, ay, R.PAGES_PER_JUZ, title_rule) if page_fn is R.fixed_pages else page_fn(txt, ay, R.PAGES_PER_JUZ)
        book += [dict(juz=j + 1, ayahs=pa, rows=R.page_rows(txt, pa)) for pa in cuts]
    return book


def naturals(book):
    return [[r[2] for r in p["rows"] if r[0] == "text"] for p in book]


def stats(book, sigma=SIGMA, squeeze=True):
    nat = naturals(book)
    W = max(max(n) for n in nat) * (1 - sigma)
    pages = [[W / x for x in n] for n in nat]
    keep = [[x for x in p if x <= 1.8] for p in pages]
    s = np.array([x for k in keep for x in k])
    ls = np.log(s)
    pm = [np.mean(np.log(k)) for k in keep]
    jm = {}
    for p, k in zip(book, keep):
        jm.setdefault(p["juz"], []).extend(np.log(k))
    jmean = {j: np.mean(v) for j, v in jm.items()}
    fill = [float(np.mean(p)) for p in pages]
    out = dict(type_size=LW / W, stretch_median=float(np.median(s)), stretch_p5=float(np.percentile(s, 5)),
               stretch_p95=float(np.percentile(s, 95)), stretch_max=float(max(max(p) for p in pages)),
               spread_in_page=float(np.median([np.std(np.log(k)) for k in keep if len(k) >= 2])),
               spread_all=float(ls.std()),
               spread_between_pages=float(math.sqrt(np.mean([(m - jmean[p["juz"]]) ** 2 for p, m, k in zip(book, pm, keep) for _ in k]))),
               sparsest_page=max(fill), densest_page=min(fill),
               sparsest_page_number=int(np.argmax(fill)) + 1, densest_page_number=int(np.argmin(fill)) + 1,
               lines_compressed=float((s < 1).mean()))
    if squeeze:
        xs = [R.justify(txt.font, " ".join(r[1]), W).x_scale for p in book for r in p["rows"] if r[0] == "text" and r[2] > W]
        n = sum(len(x) for x in nat)
        out["lines_squeezed"] = sum(1 for x in xs if x < 0.999) / n
        out["squeeze_max"] = 1 - min(xs) if xs else 0.0
    return out


def title_rows(book):
    return [i + 1 for p in book for i, r in enumerate(p["rows"]) if r[0] == "title"]


def juz30(W, sigma, rule, exempt=False, pages=R.JUZ30_PAGES_AS_JUZ, cap=R.JUZ30_MAX_STRETCH):
    R.TITLE_RULE, R.TITLE_RULE_EXEMPT_WHOLE = rule, exempt
    try:
        cuts = R.juz30_pages(txt, JUZ[29], pages, W, sigma, cap, rule)
    except SystemExit:
        return dict(feasible=False)
    book = [dict(ayahs=pa, rows=R.page_rows(txt, pa, fit_width=W / (1 - sigma) if rule else None)) for pa in cuts]
    fill = [float(np.mean([W / r[2] for r in p["rows"] if r[0] == "text"])) for p in book]
    lines = [W / r[2] for p in book for r in p["rows"] if r[0] == "text"]
    span = {}
    for i, p in enumerate(book):
        for s, a in p["ayahs"]:
            span.setdefault(s, set()).add(i)
    split = sorted(s for s, pg in span.items() if len(pg) > 1 and R.header_lines(s) + R.lines_needed(
        [x for a in range(1, len(txt.suras[s - 1]["ayas"]) + 1) for _, x in txt.units(s, a)], W, txt.sp) <= R.LINES)
    R.TITLE_RULE, R.TITLE_RULE_EXEMPT_WHOLE = True, False
    return dict(feasible=True, pages=pages, fill_min=min(fill), fill_max=max(fill), short_surahs_split=split,
                titles_below_11=sum(1 for t in title_rows(book) if t > R.TITLE_MAX_ROW),
                lines_over_1_5=sum(1 for x in lines if x > 1.5), lines_centred=sum(1 for x in lines if x > 1.8))


def solve(args):
    j, W, sigma = args
    hz = J.Hizb(txt, JUZ[j])
    return j, J.best_pages(hz, W, sigma, pages=R.PAGES_PER_JUZ)[1]


def main():
    res = {}
    final = body()
    res["final"] = stats(final)
    # compression limit
    res["compression"] = {f"{s:.2f}": stats(final, s) for s in (0.10, 0.15, 0.19, 0.25, 0.35)}
    # ablations: greedy page cuts; greedy page and line cuts
    res["ablations"] = dict(final=res["final"], greedy_pages=stats(body(A66.greedy_pages)))
    joint = R.opt_lines
    R.opt_lines = A66.greedy_lines
    res["ablations"]["greedy_pages_and_lines"] = stats(body(A66.greedy_pages))
    R.opt_lines = joint
    # title rule
    no_rule = body(title_rule=False)
    rows0, rows1 = title_rows(no_rule), title_rows(final)
    changed = sum(1 for a, b in zip(no_rule, final) if a["ayahs"] != b["ayahs"])
    res["title_rule"] = dict(without=dict(titles_below_11=sum(1 for t in rows0 if t > 11), **stats(no_rule, squeeze=False)),
                             with_rule=dict(titles_below_11=sum(1 for t in rows1 if t > 11), **stats(final, squeeze=False)),
                             pages_changed=changed)
    # exact joint optimum at the final width, objective sum (log s)^2
    nat = naturals(final)
    W = max(max(n) for n in nat) * (1 - SIGMA)
    two_stage = sum(math.log(W / x) ** 2 for n in nat for x in n)
    with Pool(2) as pool:
        vals = dict(pool.map(solve, [(j, W * 1.0000001, SIGMA) for j in range(29)]))
    res["optimum"] = dict(two_stage_objective=two_stage, exact_objective=float(sum(vals.values())),
                          gap=1 - float(sum(vals.values())) / two_stage)
    # juz 30 on 24 pages
    res["juz30"] = dict(no_title_rule=juz30(W, SIGMA, False), title_rule=juz30(W, SIGMA, True),
                        whole_surah_exempt=juz30(W, SIGMA, True, True),
                        title_rule_25_pages=juz30(W, SIGMA, True, pages=25),
                        title_rule_20_pages=juz30(W, SIGMA, True, pages=20))
    # mean stretch per juz
    per = {}
    for p, n in zip(final, nat):
        per.setdefault(p["juz"], []).extend(math.log(W / x) for x in n if W / x <= 1.8)
    res["per_juz_mean_stretch"] = [math.exp(np.mean(per[j])) for j in range(1, 30)]
    json.dump(res, open(os.path.join(DATA, "juz_design.json"), "w"), indent=1)
    for k, v in res.items():
        print(k, json.dumps(v, default=float)[:900])


if __name__ == "__main__":
    main()
