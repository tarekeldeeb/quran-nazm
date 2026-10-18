"""Does DigitalKhatt's natural width stand in for what the calligrapher wrote?

    python scripts/73_scan_validation.py PKG     # PKG: unpacked quran-qcf4 1.1.0 npm package
                                                 # writes data/scan_validation.json

Every stretch figure for the print is the line width over the DigitalKhatt (DK)
natural width of the line's text. The calligrapher's own widths come from QCF4, the
King Fahd Complex's font of the 1441H print, in which every word of every page is a
glyph traced from the print (`npm pack quran-qcf4@1.1.0`, the source quran-madina-html
already uses for the print's line breaks). A word's ink width in QCF4 is its width on
the page, as written on that line, with whatever elongation or scaling it received.

  words   The same word recurs many times, written longer or shorter as its line
          needed. The median of its written widths over its occurrences estimates the
          calligrapher's natural width of that word; it is compared with DK's natural
          width of the same word (words seen at least MIN_OCC times).
  lines   The calligrapher-natural width of a full line is the sum of its words'
          medians (DK width times the global ratio for rarer words); the print's
          stretch measured that way is compared with DK's stretch, and both with the
          letter-count proxy.

Full text lines of juz 1-29 (pages 3-581) whose words match one to one.
"""
import json
import os
import sys
from collections import defaultdict

import numpy as np
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import DATA, QMH

import render_mushaf as R  # noqa: E402  (puts quran-madina-html's justifier on the path)
import justify as J  # noqa: E402

MIN_OCC = 5
PAUSE = set("ۖۗۘۙۚۛۜ۞۩")


class Qcf:
    def __init__(self, pkg):
        self.pkg, self.fonts = pkg, {}

    def ink(self, font, code):
        if font not in self.fonts:
            t = TTFont(os.path.join(self.pkg, "fonts-woff2", f"{font}_W.woff2"))
            self.fonts[font] = (t.getBestCmap(), t.getGlyphSet(), t["hmtx"], {})
        cmap, gs, hmtx, cache = self.fonts[font]
        if code not in cache:
            g = cmap[code]
            pen = BoundsPen(gs)
            gs[g].draw(pen)
            b = pen.bounds
            cache[code] = (b[2] - b[0] if b else 0, hmtx[g][0])
        return cache[code]


def print_words():
    """(page, line) -> DK text of each word, markers left out, from quran-madina-html."""
    db = json.load(open(os.path.join(QMH, "assets", "db", "v2", "Madina-1441H.json")))
    words = defaultdict(list)
    for sura in db["suras"]:
        for aya in sura["ayas"][2:]:
            p, last = aya["p"], None
            for part in aya["r"]:
                if last is not None and part["l"] < last:
                    p += 1
                last = part["l"]
                words[(p, part["l"])] += [w for w in part["t"].split() if not w.startswith(R.MARK)]
    return db, words


def main(pkg):
    txt = R.Text()
    db, words = print_words()
    full = {(o["p"], o["l"]): o for o in json.load(open(os.path.join(DATA, "m_1441H.json"))) if o["full"]}
    q = Qcf(pkg)
    lines, mismatched = [], 0
    for p in range(3, 582):
        page = json.load(open(os.path.join(pkg, "pages", f"{p:03d}.json"), encoding="utf-8"))
        for line in page["lines"]:
            key = (p, line["line"])
            if key not in full:
                continue
            ws = [w for w in line["words"] if w["type"] == "word" and not w["text"].startswith("#")]
            dk = words.get(key, [])
            if not ws:
                continue
            if len(ws) != len(dk):
                mismatched += 1
                continue
            adv = sum(q.ink(w["font"], w["code"])[1] for w in line["words"] if w["type"] in ("word", "end"))
            ink = [q.ink(w["font"], w["code"])[0] / adv for w in ws]     # share of the line
            nat = [J.width(txt.font, w) / (full[key]["target"] * 1000) for w in dk]
            norm = ["".join(c for c in w if c not in PAUSE) for w in dk]
            lines.append(dict(p=p, l=line["line"], words=norm, ink=ink, nat=nat,
                              dk_stretch=1 / full[key]["ratio"], letters=full[key]["letters"]))
    # words: written width over occurrences vs DK natural width
    occ = defaultdict(list)
    dkw = {}
    for ln in lines:
        for w, i, n in zip(ln["words"], ln["ink"], ln["nat"]):
            occ[w].append(i)
            dkw[w] = n
    types = [w for w, v in occ.items() if len(v) >= MIN_OCC]
    med = {w: float(np.median(occ[w])) for w in types}
    x = np.log([dkw[w] for w in types])
    y = np.log([med[w] for w in types])
    fit = np.polyfit(x, y, 1)
    res = y - np.polyval(fit, x)
    within = [float(np.std(np.log(occ[w]))) for w in types]
    alpha = float(np.exp(np.median(y - x)))
    # lines: calligrapher-natural width of the words vs DK's
    cal, dks, let, cover = [], [], [], []
    for ln in lines:
        c = sum(med.get(w, n * alpha) for w, n in zip(ln["words"], ln["nat"]))
        cal.append(c)
        dks.append(ln["dk_stretch"])
        let.append(ln["letters"])
        cover.append(np.mean([w in med for w in ln["words"]]))
    # the same on the recurring words alone (no DK fallback): their calligrapher-natural
    # width against their DK width and their letter count, per line
    import re
    letter = re.compile(r"[ء-غف-يٱ]")
    cc, dc, lc = [], [], []
    for ln in lines:
        k = [(w, n) for w, n in zip(ln["words"], ln["nat"]) if w in med]
        if len(k) >= 4:
            cc.append(sum(med[w] for w, _ in k))
            dc.append(sum(n for _, n in k))
            lc.append(sum(len(letter.findall(w)) for w, _ in k))
    cc, dc, lc = np.log(cc), np.log(dc), np.log(lc)
    covered = dict(lines=len(cc), r_dk=float(np.corrcoef(cc, dc)[0, 1]), r_letters=float(np.corrcoef(cc, lc)[0, 1]),
                   residual_sd_dk=float((cc - np.polyval(np.polyfit(dc, cc, 1), dc)).std()),
                   residual_sd_letters=float((cc - np.polyval(np.polyfit(lc, cc, 1), lc)).std()))
    cal = np.log(1 / np.array(cal))
    cal -= np.median(cal)
    ldk = np.log(dks)
    ldk_c = ldk - np.median(ldk)
    llet = np.log(np.mean(let) / np.array(let))
    written = np.log([sum(ln["ink"]) for ln in lines])
    lfit = np.polyfit(ldk_c, cal, 1)
    # the print's spread inside a page, measured both ways on the same lines
    pg = np.array([ln["p"] for ln in lines])
    def in_page(v):
        return float(np.median([v[pg == p].std() for p in np.unique(pg) if (pg == p).sum() >= 10]))
    def between_pages(v):
        m = {p: v[pg == p].mean() for p in np.unique(pg)}
        return float(np.std([m[p] for p in pg]))
    out = dict(lines=len(lines), lines_unmatched=mismatched, words=int(sum(len(v) for v in occ.values())),
               word_types=len(occ), word_types_used=len(types), word_occurrences_covered=float(
                   sum(len(occ[w]) for w in types) / sum(len(v) for v in occ.values())),
               word_r=float(np.corrcoef(x, y)[0, 1]), word_slope=float(fit[0]), word_residual_sd=float(res.std()),
               word_within_type_sd_median=float(np.median(within)),
               line_r_dk=float(np.corrcoef(ldk_c, cal)[0, 1]), line_slope=float(lfit[0]),
               line_residual_sd=float((cal - np.polyval(lfit, ldk_c)).std()),
               line_r_letters=float(np.corrcoef(llet, cal)[0, 1]),
               line_r_words=float(np.corrcoef(np.log([np.mean([len(l["words"]) for l in lines]) / len(l["words"])
                                                        for l in lines]), cal)[0, 1]),
               in_page_dk=in_page(ldk), in_page_calligrapher=in_page(cal),
               between_pages_dk=between_pages(ldk), between_pages_calligrapher=between_pages(cal),
               sd_dk=float(ldk.std()), sd_calligrapher=float(cal.std()),
               line_coverage_mean=float(np.mean(cover)),
               written_share_median=float(np.exp(np.median(written))),
               recurring_words_only=covered,
               r_dk_written_share=float(np.corrcoef(ldk, written)[0, 1]))
    json.dump(dict(summary=out, word_types=[dict(w=w, n=len(occ[w]), dk=dkw[w], median=med[w],
                                                 sd_log=float(np.std(np.log(occ[w])))) for w in types]),
              open(os.path.join(DATA, "scan_validation.json"), "w"), ensure_ascii=False, indent=0)
    for k, v in out.items():
        print(f"{k:28s} {v}")


if __name__ == "__main__":
    main(sys.argv[1])
