"""Pen weight of the print measured on vector outlines instead of the 100 ppi scan.

    python scripts/74_pen_weight_vector.py PKG   # PKG: unpacked quran-qcf4 1.1.0 npm package
                                                 # writes data/pen_weight_vector.json

QCF4, the King Fahd Complex's font of the 1441H print, traces every word of every page
as a glyph. Each word glyph of a full line is rasterised at six times the scan's
resolution (about 600 ppi; a stroke is about 12 px wide instead of 2) and measured as
script 20 measures the scan: mean pen width = ink area / skeleton length, and ink per
letter (letters of the DigitalKhatt text, as for the scan). Ayah markers are left
out, as they are masked on the scan.

The same summaries as the paper's scan figures are computed on the same lines (full
lines of the pages made only of text, juz 1-29), and every line is compared with its
scan measurement (data/w_1441H.json). A tracing may smooth the pen, so agreement
between the two is a cross-check of both.
"""
import json
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor

import freetype
import numpy as np
from fontTools.ttLib import TTFont
from skimage.morphology import skeletonize

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import DATA, QMH, WORK

UP = 6                       # times the scan resolution
SCAN_LINE_PX = 640           # width of a full line on the scan
PKG = None
LETTER = re.compile(r"[ء-غف-يٱ]")


def ttf(pkg, font):
    out = os.path.join(WORK, "qcf4", f"{font}.ttf")
    if not os.path.exists(out):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        t = TTFont(os.path.join(pkg, "fonts-woff2", f"{font}_W.woff2"))
        t.flavor = None
        t.save(out)
    return out


def page(p):
    data = json.load(open(os.path.join(PKG, "pages", f"{p:03d}.json"), encoding="utf-8"))
    faces, out = {}, []
    for line in data["lines"]:
        ws = [w for w in line["words"] if w["type"] in ("word", "end")]
        if not ws or any(w["type"] in ("surah_header", "bismillah") for w in line["words"]):
            continue
        for w in ws:
            if w["font"] not in faces:
                f = freetype.Face(ttf(PKG, w["font"]))
                faces[w["font"]] = f
        adv = 0
        for w in ws:
            f = faces[w["font"]]
            f.set_char_size(f.units_per_EM * 64)
            f.load_char(w["code"], freetype.FT_LOAD_NO_SCALE)
            adv += f.glyph.advance.x
        scale = SCAN_LINE_PX * UP / adv            # px per font unit
        area = length = 0
        for w in ws:
            if w["type"] != "word":
                continue                             # ayah markers are masked on the scan too
            f = faces[w["font"]]
            f.set_pixel_sizes(0, max(1, round(f.units_per_EM * scale)))
            f.load_char(w["code"], freetype.FT_LOAD_RENDER)
            b = f.glyph.bitmap
            if not b.width:
                continue
            img = np.array(b.buffer, np.uint8).reshape(b.rows, b.pitch)[:, :b.width] >= 128
            area += int(img.sum())
            length += int(skeletonize(img).sum())
        letters = sum(len(LETTER.findall(w["text"])) for w in ws if w["type"] == "word")
        if length:
            out.append(dict(p=p, l=line["line"], adv=adv, sw=area / length / UP, ink=area / UP / UP,
                            letters=letters))
    return out


def summary(rows, scan):
    sw = np.array([r["sw"] for r in rows])
    ink = np.array([r["ink"] for r in rows])
    ratio = np.array([r["ratio"] for r in rows])
    ipl = ink / np.array([r["letters"] for r in rows])
    by = {}
    for r in rows:
        by.setdefault(r["p"], {})[r["l"]] = r
    in_page = [max(x["sw"] for x in v.values()) / min(x["sw"] for x in v.values()) for v in by.values() if len(v) >= 10]
    sparse, crowded = ratio < 0.9, ratio > 1.1
    pages = sorted(by)
    page_sw = [np.mean([x["sw"] for x in by[p].values()]) for p in pages]
    late = [s for p, s in zip(pages, page_sw) if 540 <= p <= 580]
    mid = [s for p, s in zip(pages, page_sw) if 480 <= p < 540]
    pair = lambda p, a, b: by[p][b]["sw"] / by[p][a]["sw"] if p in by and a in by[p] and b in by[p] else None
    psw = dict(zip(pages, page_sw))
    out = dict(lines=len(rows), pages=len(by),
               heavy_over_light_5_95=float(np.percentile(sw, 95) / np.percentile(sw, 5)),
               in_page_max_over_min_median=float(np.median(in_page)),
               sparse_over_crowded=float(sw[sparse].mean() / sw[crowded].mean()),
               ink_per_letter_5_95=float(np.percentile(ipl, 95) / np.percentile(ipl, 5)),
               r_ink_per_letter_ratio=float(np.corrcoef(ipl, ratio)[0, 1]),
               r_sw_ratio=float(np.corrcoef(sw, ratio)[0, 1]),
               r_page_sw_page=float(np.corrcoef([p for p in pages if p <= 500], [s for p, s in zip(pages, page_sw) if p <= 500])[0, 1]),
               late_rise=float(np.mean(late) / np.mean(mid)) if late and mid else None,
               p102_l5_over_l4=pair(102, 4, 5),
               p561_over_p563=float(psw[561] / psw[563]) if 561 in psw and 563 in psw else None)
    if scan:
        out["stroke_px_at_600ppi"] = float(np.median(sw) * UP)
    return out


def main(pkg):
    global PKG
    PKG = pkg
    db = json.load(open(os.path.join(QMH, "assets", "db", "v2", "Madina-1441H.json")))
    text_only = {p for p in range(3, 582) if all(r["k"] == "text" for r in db["lines"][p - 1])}
    full = {(o["p"], o["l"]): o for o in json.load(open(os.path.join(DATA, "m_1441H.json"))) if o["full"]}
    scan = {(o["p"], o["l"]): o for o in json.load(open(os.path.join(DATA, "w_1441H.json"))) if o.get("full")}
    fonts = {w["font"] for p in range(3, 582)
             for ln in json.load(open(os.path.join(pkg, "pages", f"{p:03d}.json")))["lines"] for w in ln["words"]
             if w["type"] in ("word", "end")}
    for f in fonts:
        ttf(pkg, f)                                  # convert once, before the workers start
    with ProcessPoolExecutor(initializer=_init, initargs=(pkg,)) as ex:
        rows = [r for rs in ex.map(page, sorted(text_only)) for r in rs]
    rows = [dict(r, ratio=full[(r["p"], r["l"])]["ratio"], letters=full[(r["p"], r["l"])]["letters"]) for r in rows if (r["p"], r["l"]) in full]
    both = [(r, scan[(r["p"], r["l"])]) for r in rows if (r["p"], r["l"]) in scan]
    sv = np.log([r["sw"] for r, _ in both])
    ss = np.log([s["sw"] for _, s in both])
    iv = np.log([r["ink"] / r["letters"] for r, _ in both])
    is_ = np.log([s["ink"] / s["letters"] for _, s in both])
    scan_rows = [dict(p=s["p"], l=s["l"], sw=s["sw"], ink=s["ink"], letters=s["letters"], ratio=s["ratio"]) for _, s in both]
    res = dict(vector=summary([r for r, _ in both], True), scan=summary(scan_rows, False),
               agreement=dict(lines=len(both), r_sw=float(np.corrcoef(sv, ss)[0, 1]),
                              r_ink_per_letter=float(np.corrcoef(iv, is_)[0, 1]),
                              sd_vector=float(sv.std()), sd_scan=float(ss.std())),
               lines=[dict(p=r["p"], l=r["l"], sw=r["sw"], ink=r["ink"], letters=r["letters"]) for r in rows])
    json.dump(res, open(os.path.join(DATA, "pen_weight_vector.json"), "w"), indent=0)
    for k in ("vector", "scan", "agreement"):
        print(k, json.dumps(res[k], indent=1))


def _init(pkg):
    global PKG
    PKG = pkg


if __name__ == "__main__":
    main(sys.argv[1])
