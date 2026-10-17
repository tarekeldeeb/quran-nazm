"""How far is the renderer's layout from the exact optimum? (hizbs 1-58)

    python scripts/68_joint_optimum.py        # writes data/joint_optimum.json (about 5 minutes)

The renderer breaks a hizb in two stages: page cuts that balance natural text
width (shaped advances in the DigitalKhatt font, headers counted as lines), then
line cuts inside each page. joint_layout.py solves both together, exactly, for
the objective sum of (log stretch)^2 over all lines, and bisects on the common
line width W for the largest type at which every hizb still fits. Its page-level
optimum is checked against an integer programme solved by HiGHS.

Variants compared:
  current       the renderer (two-stage), W = longest natural line x 0.75
  density_cap   two-stage, with the tightest cap on page density at which every hizb still fits
  joint_same_w  joint optimum at the current W
  joint_best_w  joint optimum at the smallest feasible W

Also reported: the standard deviation of log stretch split into between-hizb,
between-page and within-page parts, and, for scale, the between-hizb part if hizbs
could take 8-12 pages instead of exactly 10.
"""
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

SHRINK = 0.25
LW_MADINA = 15437.6
txt = R.Text()
HIZBS = [txt.flat[a0 - 1:a1 - 1] for a0, a1 in R.hizb_ranges()[:58]]


def two_stage(max_density=None):
    book = []
    for h, ay in enumerate(HIZBS):
        pages = R.fixed_pages(txt, ay, R.PAGES_PER_HIZB, True, max_density)
        if len(pages) != R.PAGES_PER_HIZB or any(not p for p in pages):
            return None
        book += [dict(hizb=h + 1, rows=R.page_rows(txt, p)) for p in pages]
    return book


def density(book):
    out = []
    for p in book:
        t = [r[2] for r in p["rows"] if r[0] == "text"]
        out.append(sum(t) / len(t))
    return out


def solve(args):
    h, W = args
    hz = J.Hizb(txt, HIZBS[h - 1])
    cuts, val = J.best_pages(hz, W, SHRINK)
    return h, cuts, val


def joint(W):
    with Pool(2) as pool:
        res = pool.map(solve, [(h, W) for h in range(1, 59)])
    return {h: (c, v) for h, c, v in res}


def joint_book(sol, W):
    book = []
    for h in range(1, 59):
        hz = J.Hizb(txt, HIZBS[h - 1])
        book += [dict(hizb=h, rows=J.rows_for(hz, j, i, W, W / (1 - SHRINK))) for j, i in sol[h][0]]
    return book


def metrics(book):
    nat = [[r[2] for r in p["rows"] if r[0] == "text"] for p in book]
    W = max(max(n) for n in nat) * (1 - SHRINK)
    keep = [[W / x for x in n if W / x <= 1.8] for n in nat]
    s = np.array([x for k in keep for x in k])
    fill = [float(np.mean([W / x for x in n])) for n in nat]
    ls = [(math.log(x), p["hizb"], q) for q, (p, k) in enumerate(zip(book, keep)) for x in k]
    v = np.array([a for a, _, _ in ls])
    hm = {h: np.mean([a for a, hh, _ in ls if hh == h]) for h in range(1, 59)}
    pm = {q: np.mean([a for a, _, qq in ls if qq == q]) for q in range(len(book))}
    return dict(type_size=LW_MADINA / W, stretch_median=float(np.median(s)), stretch_p95=float(np.percentile(s, 95)),
                within_page_spread=float(np.median([np.std(np.log(k)) for k in keep if len(k) >= 2])),
                sparsest_page=max(fill), densest_page=min(fill),
                objective=float(sum(math.log(W / x) ** 2 for n in nat for x in n)),
                sd_log_stretch=float(v.std()),
                sd_between_hizbs=float(math.sqrt(np.mean([(hm[h] - v.mean()) ** 2 for _, h, _ in ls]))),
                sd_between_pages=float(math.sqrt(np.mean([(pm[q] - hm[h]) ** 2 for _, h, q in ls]))),
                sd_within_pages=float(math.sqrt(np.mean([(a - pm[q]) ** 2 for a, _, q in ls]))))


def flexible_hizbs():
    """Between-hizb sd of log page density if each hizb could take 8-12 pages (580 in all)."""
    L = []
    for ay in HIZBS:
        w = sum(sum(x for _, x in txt.units(s, a)) + txt.sp * len(txt.units(s, a)) for s, a in ay)
        L.append((w, sum(R.header_lines(s) for s, a in ay if a == 1)))
    def sd(pages):
        return float(np.std(np.log([w / (p * R.LINES - h) for (w, h), p in zip(L, pages)])))
    best = (sd([10] * 58), [10] * 58)
    mean = sum(w for w, _ in L) / (580 * R.LINES)
    for t in np.linspace(0.95 * mean, 1.05 * mean, 400):
        p = [min(max(round((w / t + h) / R.LINES), 8), 12) for w, h in L]
        if sum(p) == 580 and sd(p) < best[0]:
            best = (sd(p), p)
    return dict(fixed_10=sd([10] * 58), pages_8_to_12=best[0],
                page_counts={k: best[1].count(k) for k in range(8, 13)})


def main():
    res = {}
    cur = two_stage()
    res["current"] = metrics(cur)
    W0 = max(r[2] for p in cur for r in p["rows"] if r[0] == "text") * (1 - SHRINK)
    # tightest page-density cap at which every hizb still fits
    d0 = max(density(cur))
    lo, hi = 0.9 * d0, d0
    for _ in range(12):
        mid = (lo + hi) / 2
        if two_stage(mid) is None:
            lo = mid
        else:
            hi = mid
    res["density_cap"] = metrics(two_stage(hi))
    res["density_cap"]["cap_vs_densest_page"] = hi / d0
    # exact joint optimum: check against HiGHS on two hizbs, then bisect on W
    check = {}
    for h in (2, 55):
        hz = J.Hizb(txt, HIZBS[h - 1])
        cost = hz.page_table(W0 * 1.0000001, SHRINK)
        check[h] = dict(dynamic_programme=J.best_pages(hz, W0 * 1.0000001, SHRINK, cost=cost)[1],
                        highs_milp=float(J.milp_pages(hz, cost)))
    res["milp_check"] = check
    sol0 = joint(W0 * 1.0000001)
    res["joint_same_w"] = metrics(joint_book(sol0, W0 * 1.0000001))
    lo, hi, best = 0.93 * W0, W0 * 1.0000001, sol0
    for _ in range(9):
        mid = (lo + hi) / 2
        sol = joint(mid)
        if all(v < J.INF for _, v in sol.values()):
            hi, best = mid, sol
        else:
            lo = mid
    res["joint_best_w"] = metrics(joint_book(best, hi))
    res["joint_best_w"]["width_vs_current"] = hi / W0
    res["flexible_pages_per_hizb"] = flexible_hizbs()
    json.dump(res, open(os.path.join(DATA, "joint_optimum.json"), "w"), indent=1)
    for k, v in res.items():
        print(k, {a: (round(b, 4) if isinstance(b, float) else b) for a, b in v.items()})


if __name__ == "__main__":
    main()
