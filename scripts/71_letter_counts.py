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

It also measures how the Madina boundaries (from Ghayth al-Naf' of al-Safaqisi, per
the colophon of the Complex's Hafs editions) sit against equal letter counts, in
written letters: how far each juz start lies from its equal-letter position (in
units of a juz), how far each quarter lies from the equal eighths of its own juz
(in units of a quarter), and how close cutting at the nearest ayah end could get.
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


def madina_boundaries(letters, flat):
    starts = json.load(open(os.path.join(DATA, "hafs-rub-start-ayahs.json")))
    rub = [starts[k] for k in range(1, 241)]               # flat (1-based) start ayah of each quarter
    c = np.concatenate([[0], np.cumsum(letters)])
    T = c[-1]
    juz_off = [abs(c[rub[8 * j] - 1] / T * 30 - j) for j in range(30)]
    quarter_off = []
    for j in range(30):
        a, b = c[rub[8 * j] - 1], (c[rub[8 * j + 8] - 1] if j < 29 else T)
        quarter_off += [abs((c[rub[8 * j + q] - 1] - a) / (b - a) * 8 - q) for q in range(1, 8)]
    nearest = []
    for k in range(1, 240):
        t = k / 240 * T
        i = int(np.searchsorted(c, t))
        nearest.append(min(abs(c[max(i - 1, 0)] - t), abs(c[min(i, len(c) - 1)] - t)) / T * 240)
    rl = np.diff(np.append([c[r - 1] for r in rub], T))
    jl = np.add.reduceat(rl, range(0, 240, 8))
    sura_start = {i + 1 for i, (s, a) in enumerate(flat) if a == 1}
    return dict(juz_start_offset_mean=float(np.mean(juz_off)), juz_start_offset_max=float(np.max(juz_off)),
                quarter_offset_in_juz_mean=float(np.mean(quarter_off)), quarter_offset_in_juz_max=float(np.max(quarter_off)),
                nearest_ayah_end_offset_mean=float(np.mean(nearest)), nearest_ayah_end_offset_max=float(np.max(nearest)),
                quarter_letters_cv=float(rl.std() / rl.mean()), juz_letters_cv=float(jl.std() / jl.mean()),
                juz_cv_if_quarters_independent=float(rl.std() / rl.mean() / np.sqrt(8)),
                quarters_opening_a_surah=sum(1 for r in rub if r in sura_start),
                juz_opening_a_surah=sum(1 for r in rub[::8] if r in sura_start))


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
    summary["madina_boundaries"] = madina_boundaries(M[:, 0], flat)
    json.dump(dict(summary=summary, conventions=out), open(os.path.join(DATA, "letter_counts.json"), "w"), indent=1)
    for k, v in summary.items():
        print(k, v)


if __name__ == "__main__":
    main()
