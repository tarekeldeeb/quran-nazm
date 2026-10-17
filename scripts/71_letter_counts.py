"""Letter counts of the Quran under different counting conventions, against the
report of al-Hajjaj's count and against the traditional juz.

    python scripts/71_letter_counts.py        # writes data/letter_counts.json

The report (Ibn Abi Dawud, Kitab al-Masahif; relayed by Ibn Kathir, Tafsir, intro.)
gives 340,740 letters, the half at Al-Kahf 19, thirds at Al-Tawba 100 and Al-Shu'ara
100, and sevenths at Al-Nisa 55, Al-A'raf 147, Al-Ra'd 35, Al-Hajj 34, Al-Ahzab 36
and Al-Fath 6. Classical counts differ in what counts as a letter, so every
combination of six choices is tried on the Uthmani text of the 1441H data:

  wasla    drop the connecting alef (not pronounced in connected reading)
  silent   drop letters marked silent (small high rounded or rectangular zero)
  small    add the small letters pronounced but not written (dagger alef, small waw/yeh)
  shadda   count a doubled letter twice
  maddah   count a long vowel's lengthening as a letter
  tanween  count the nunation as a letter

Ayah markers are not counted. A report point is taken at the end of its ayah.
"""
import itertools
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import DATA

import render_mushaf as R

BASE = re.compile(r"[ء-غف-يٱ]")
SILENT = re.compile(r"[ء-غف-يٱ][ً-ْٕٔ͏]*[۟۠]")
PARTS = dict(
    wasla=lambda t: t.count("ٱ"),
    silent=lambda t: len(SILENT.findall(t)),
    small=lambda t: sum(t.count(c) for c in "ٰۥۦۧۨ"),
    shadda=lambda t: t.count("ّ"),
    maddah=lambda t: t.count("ٓ"),
    tanween=lambda t: sum(t.count(c) for c in "ًࣰٌࣱٍࣲ"),
)
REPORT = {"1/2": ((18, 19), 1 / 2), "1/3": ((9, 100), 1 / 3), "2/3": ((26, 100), 2 / 3),
          "1/7": ((4, 55), 1 / 7), "2/7": ((7, 147), 2 / 7), "3/7": ((13, 35), 3 / 7),
          "4/7": ((22, 34), 4 / 7), "5/7": ((33, 36), 5 / 7), "6/7": ((48, 6), 6 / 7)}


def main():
    txt = R.Text()
    flat = txt.flat
    rows = []
    for s, a in flat:
        t = " ".join(w for w in txt.suras[s - 1]["ayas"][a - 1].split() if not w.startswith(R.MARK))
        rows.append([len(BASE.findall(t))] + [f(t) for f in PARTS.values()])
    M = np.array(rows, float)
    names = list(PARTS)
    juz = R.juz_ranges()
    at = {k: flat.index(v[0]) for k, v in REPORT.items()}
    out = []
    for flags in itertools.product([0, 1], repeat=len(names)):
        w = np.array([1] + [(-f if n in ("wasla", "silent") else f) for f, n in zip(flags, names)], float)
        per = M @ w
        c = np.cumsum(per)
        T = c[-1]
        jl = np.array([per[a0 - 1:a1 - 1].sum() for a0, a1 in juz])
        dev = {k: float((c[at[k]] / T - REPORT[k][1]) * 100) for k in REPORT}
        out.append(dict(convention=[n for f, n in zip(flags, names) if f], total=int(T),
                        report_point_deviation_pct=dev,
                        mean_abs_deviation_without_2_3=float(np.mean([abs(v) for k, v in dev.items() if k != "2/3"])),
                        juz16_start_pct=float(c[juz[15][0] - 2] / T * 100), juz11_start_pct=float(c[juz[10][0] - 2] / T * 100),
                        juz21_start_pct=float(c[juz[20][0] - 2] / T * 100),
                        juz_max_over_min=float(jl.max() / jl.min()), juz_cv=float(jl.std() / jl.mean())))
    rng = lambda key: [min(o[key] for o in out), max(o[key] for o in out)]
    summary = {k: rng(k) for k in ("total", "mean_abs_deviation_without_2_3", "juz16_start_pct", "juz11_start_pct",
                                    "juz21_start_pct", "juz_max_over_min", "juz_cv")}
    summary["report_2_3_deviation_pct"] = [min(o["report_point_deviation_pct"]["2/3"] for o in out),
                                           max(o["report_point_deviation_pct"]["2/3"] for o in out)]
    summary["closest_to_340740"] = min(out, key=lambda o: abs(o["total"] - 340740))
    json.dump(dict(summary=summary, conventions=out), open(os.path.join(DATA, "letter_counts.json"), "w"), indent=1)
    for k, v in summary.items():
        print(k, v)


if __name__ == "__main__":
    main()
