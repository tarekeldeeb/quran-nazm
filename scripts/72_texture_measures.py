"""Texture measures that Quran-Nazm does not optimise, for the print and for Nazm.

    python scripts/72_texture_measures.py        # writes data/texture_measures.json

Nazm's page and line breaks balance natural width, so the spread of line stretch is
its own objective. These measures are not:

  words per line            mean and s.d. over full lines
  elongated words per line  words carrying any elongation feature
  elongation share          width added by elongation, over the line width
  word gap share            one ordinary word gap over the line width (mean per line)
  horizontally scaled lines lines whose letters are scaled to fit
  distortion                share of lines whose letters are scaled horizontally (the
                            print's reproduction narrows words by `c`, rarely the line by
                            `x`; Nazm scales the line), and by how much; a scale k thins
                            vertical strokes by 1 - k

The print is measured on the DigitalKhatt reproduction of its lines in quran-madina-html
(per-word `jpNN` alternates, per-line spaces `s`, narrowing `c`, scale `x`), full
lines of juz 1-29 (pages 1-581). Nazm is measured on its own justified lines (juz
1-29, centred lines left out). Widths come from shaping each word with and without
its features in the same font.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import DATA, QMH

import render_mushaf as R  # noqa: E402  (puts quran-madina-html's justifier on the path)
import justify as J  # noqa: E402


def feats(spec):
    out = {}
    for kv in filter(None, spec.split(",")):
        k, v = kv.split("=")
        out[k] = int(v)
    return out


def print_lines(txt):
    db = json.load(open(os.path.join(QMH, "assets", "db", "v2", "Madina-1441H.json")))
    LW = db["line_width"] * 1000
    words = {}  # (page, line) -> [(text, feature dict)]
    for sura in db["suras"]:
        for aya in sura["ayas"][2:]:
            p, last = aya["p"], None
            for part in aya["r"]:
                if last is not None and part["l"] < last:
                    p += 1                       # the ayah continues on the next page
                last = part["l"]
                ws = part["t"].split()
                for w, f in zip(ws, part["f"] + [""] * (len(ws) - len(part["f"]))):
                    words.setdefault((p, part["l"]), []).append((w, feats(f)))
    out = []
    for p, page in enumerate(db["lines"], 1):
        if p >= 582:
            break
        for l, row in enumerate(page, 1):
            if row["k"] != "text" or abs(row["w"] - db["line_width"]) > 1e-3 or (p, l) not in words:
                continue
            ws = [(w, f) for w, f in words[(p, l)] if not w.startswith(R.MARK)]
            elong = sum(J.width(txt.font, w, {k: v for k, v in f.items()}) - J.width(txt.font, w) for w, f in ws if f)
            gaps = [g * 1000 for g in row.get("s", [])]
            out.append(dict(words=len(ws), elongated=sum(1 for _, f in ws if f), elong_share=elong / LW,
                            gap_share=float(np.mean(gaps)) / LW if gaps else None,
                            scaled="x" in row, narrowed=bool(row.get("c")),
                            scale=row.get("c", 1.0) * row.get("x", 1.0)))
    return out


def nazm_lines(txt):
    book, W, _ = R.build_layout(txt, 0.19, "juz")
    out = []
    for p in book:
        if p.get("juz", 30) > 29 or p.get("opening"):
            continue
        for r in p["rows"]:
            if r[0] != "text" or W / r[2] > 1.8:
                continue
            text = " ".join(r[1])
            res = R.justify(txt.font, text, W)
            line = J.analyze_line(text)
            ws = [w for w in line.words if not w.text.startswith(R.MARK)]
            elong, n_el = 0.0, 0
            for w in line.words:
                f = {i: res.features[i] for i in range(w.start, w.end + 1) if i in res.features}
                if not f or w.text.startswith(R.MARK):
                    continue
                n_el += 1
                elong += J.width(txt.font, w.text, J.to_hb_features(f, w.start, w.start, w.end)) - J.width(txt.font, w.text)
            out.append(dict(words=len(ws), elongated=n_el, elong_share=elong / W, gap_share=res.simple_spacing / W,
                            scaled=res.x_scale < 0.999, narrowed=False, scale=res.x_scale))
    return out


def summary(lines):
    a = lambda k: np.array([l[k] for l in lines if l[k] is not None], float)
    w, e, es, g = a("words"), a("elongated"), a("elong_share"), a("gap_share")
    return dict(lines=len(lines), words_mean=float(w.mean()), words_sd=float(w.std()),
                elongated_words_mean=float(e.mean()), lines_with_elongation=float((e > 0).mean()),
                elongated_words_p95=float(np.percentile(e, 95)),
                elong_share_mean=float(es.mean()), elong_share_p95=float(np.percentile(es, 95)),
                elong_share_sd=float(es.std()),
                gap_share_median=float(np.median(g)), gap_share_p5=float(np.percentile(g, 5)),
                gap_share_p95=float(np.percentile(g, 95)), gap_share_sd=float(g.std()),
                lines_scaled=float(np.mean([l["scaled"] for l in lines])),
                lines_narrowed=float(np.mean([l["narrowed"] for l in lines])),
                **distortion(a("scale")))


def distortion(scale):
    """Horizontal scaling of letters (the print's reproduction narrows words, Nazm
    scales lines); a scale of k thins vertical strokes by 1 - k."""
    d = 1 - scale[scale < 0.999]
    return dict(distorted_lines=float((scale < 0.999).mean()), distorted_over_5pct=float((scale < 0.95).mean()),
                distortion_mean=float(d.mean()) if len(d) else 0.0,
                distortion_p95=float(np.percentile(d, 95)) if len(d) else 0.0,
                distortion_max=float(d.max()) if len(d) else 0.0,
                distortion_mean_all_lines=float((1 - scale).mean()))


def main():
    txt = R.Text()
    res = dict(madina_1441h=summary(print_lines(txt)), nazm=summary(nazm_lines(txt)))
    json.dump(res, open(os.path.join(DATA, "texture_measures.json"), "w"), indent=1)
    for k in res["nazm"]:
        print(f"{k:28s} {res['madina_1441h'][k]:>10.4f} {res['nazm'][k]:>10.4f}")


if __name__ == "__main__":
    main()
