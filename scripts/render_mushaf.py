"""Typeset the complete Quran with the Quran-Nazm rules and write a vector PDF.

Rules (the decisions recorded in docs/findings.md):
  * Every hizb (1-58) fills exactly 10 pages of 15 lines.
  * Every page ends at the end of an ayah; no line starts with an ayah marker.
  * Layout of a hizb: set the whole hizb as one unstretched DigitalKhatt line,
    cut it into 10 pages at ayah ends (all nine cuts chosen together so each page
    carries the same amount of text, surah headers counted as the lines they use),
    then cut each page into equal lines at word boundaries (all cuts chosen together).
  * A surah always starts on a new line, preceded by its header (title line plus
    basmala line; one line for Al-Fatiha, whose basmala is ayah 1, and for Al-Tawba).
  * One line width for the whole book: the longest natural line in hizbs 1-58,
    narrowed by the shrink limit (default 25%). Lines are then justified with the
    DigitalKhatt stretching rules, or compressed (spaces, narrow forms, then a
    horizontal scale as last resort).
  * Juz 30 (hizbs 59-60) is the declared exception: its pages are filled in
    sequence at the same line width and type size, still ending on ayahs.

Usage:
    python scripts/00_prepare.py                 # once: fonts out of quran-madina-html
    python scripts/render_mushaf.py              # whole Mushaf -> build/quran-nazm.pdf
    python scripts/render_mushaf.py --pages 1-20 --out build/sample.pdf
    python scripts/render_mushaf.py --shrink 0.20
"""
import argparse
import json
import math
import os
import sys
import time
import zlib

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import DATA, QMH, WORK

sys.path.insert(0, os.path.join(QMH, "src", "db", "v2"))
import justify as J  # noqa: E402  (HarfBuzz justifier from quran-madina-html v2)
import uharfbuzz as hb  # noqa: E402
from fontTools.pens.basePen import BasePen  # noqa: E402
from fontTools.ttLib import TTFont  # noqa: E402

PAGES_PER_HIZB = 10
LINES = 15
MARK = "۝"
FONT_PATH = os.path.join(WORK, "madina.otf")
LABEL_FONT_PATH = os.path.join(WORK, "amiri.ttf")  # Amiri Quran: digits for page numbers and running heads
DB_PATH = os.path.join(QMH, "assets", "db", "v2", "Madina-1441H.json")

# Physical page (points). Text block 110 mm wide, 15 rows; row pitch keeps the
# Madina proportion of 0.1086 x line width measured on the 1441H print.
MM = 72 / 25.4
PAGE_W, PAGE_H = 145 * MM, 210 * MM
BLOCK_W = 110 * MM
PITCH_RATIO = 0.1086
BASELINE_IN_ROW = 0.68
INK = (0.09, 0.09, 0.09)
GREEN = (0.18, 0.42, 0.33)
PALE = (0.93, 0.96, 0.94)

AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def ar_num(n):
    """Arabic-Indic digits, pre-reversed: the label is shaped as one right-to-left
    run without bidi reordering, which would otherwise flip multi-digit numbers."""
    return str(n).translate(AR_DIGITS)[::-1]


# --------------------------------------------------------------------- text
class Text:
    def __init__(self):
        self.font = hb.Font(hb.Face(open(FONT_PATH, "rb").read()))
        self.label_font = hb.Font(hb.Face(open(LABEL_FONT_PATH, "rb").read()))
        self.sp = J.width(self.font, " ")
        self.aya_sp = self.sp * J.AYA_SPACE
        self._w = {}
        db = json.load(open(DB_PATH))
        self.suras = []
        for s, su in enumerate(db["suras"], 1):
            ayas = [" ".join(r["t"].strip() for r in a["r"] if r["t"].strip()) for a in su["ayas"][2:]]
            self.suras.append(dict(n=s, title=su["name"], ayas=ayas))
        self.basmala = " ".join(r["t"] for r in db["suras"][1]["ayas"][1]["r"]).strip()
        self.flat = [(su["n"], i + 1) for su in self.suras for i in range(len(su["ayas"]))]
        assert len(self.flat) == 6236

    def width(self, t):
        if t not in self._w:
            self._w[t] = J.width(self.font, t)
        return self._w[t]

    def units(self, s, a):
        """Words of an ayah; the ayah marker is glued to the word before it, so a
        line can never start with a marker."""
        out = []
        for tk in self.suras[s - 1]["ayas"][a - 1].split():
            if tk.startswith(MARK) and out:
                t, w = out[-1]
                out[-1] = (t + " " + tk, w + self.aya_sp + self.width(tk))
            else:
                out.append((tk, self.width(tk)))
        return out


def header_lines(s):
    return 1 if s in (1, 9) else 2


# ------------------------------------------------------------------- layout
def opt_lines(ws, n, sp):
    """Cut a run of words into exactly n lines, minimising the squared deviation
    of each line's natural width from the mean (all cuts chosen together)."""
    m = len(ws)
    n = max(1, min(n, m))
    cum = np.concatenate([[0], np.cumsum(np.array(ws) + sp)])
    tgt = cum[-1] / n
    INF = 1e30
    best = np.full((n + 1, m + 1), INF)
    back = np.zeros((n + 1, m + 1), int)
    best[0][0] = 0
    for k in range(1, n + 1):
        for e in range(k, m - (n - k) + 1):
            for s in range(max(k - 1, e - 40), e):
                if best[k - 1][s] >= INF:
                    continue
                c = best[k - 1][s] + (cum[e] - cum[s] - tgt) ** 2
                if c < best[k][e]:
                    best[k][e], back[k][e] = c, s
    cuts, k = [m], n
    while k:
        cuts.append(back[k][cuts[-1]])
        k -= 1
    cuts = cuts[::-1]
    return list(zip(cuts[:-1], cuts[1:]))


def allocate(widths, total, caps):
    """Share `total` lines among the surah segments of a page: each line goes to the
    segment whose lines are currently the longest on average (so no segment is
    left crowded), never more lines than a segment has words."""
    alloc = [1] * len(widths)
    while sum(alloc) < total:
        open_ = [i for i in range(len(widths)) if alloc[i] < caps[i]]
        if not open_:
            break
        i = max(open_, key=lambda i: widths[i] / alloc[i])
        alloc[i] += 1
    return alloc


def page_rows(txt, ayahs, n_lines=None):
    """Turn the ayahs of one page into rows: ('title', s), ('basmala',), ('text', [unit texts], natural)."""
    segs = []
    for s, a in ayahs:
        if a == 1 or not segs:
            segs.append(dict(s=s, head=(a == 1), units=[]))
        segs[-1]["units"] += txt.units(s, a)
    heads = sum(header_lines(g["s"]) for g in segs if g["head"])
    total = (LINES - heads) if n_lines is None else n_lines
    widths = [sum(w for _, w in g["units"]) + txt.sp * len(g["units"]) for g in segs]
    rows = []
    for g, n in zip(segs, allocate(widths, total, [len(g['units']) for g in segs])):
        if g["head"]:
            rows.append(("title", g["s"]))
            if header_lines(g["s"]) == 2:
                rows.append(("basmala",))
        ws = [w for _, w in g["units"]]
        for a, b in opt_lines(ws, n, txt.sp):
            nat = sum(ws[a:b]) + txt.sp * (b - a - 1)
            rows.append(("text", [t for t, _ in g["units"][a:b]], nat))
    return rows


def hizb_ranges():
    starts = json.load(open(os.path.join(DATA, "hafs-rub-start-ayahs.json")))
    return [(starts[1 + 4 * h], starts[1 + 4 * h + 4] if h < 59 else 6237) for h in range(60)]


def fixed_hizb_pages(txt, ayahs):
    """Nine page cuts at ayah ends, chosen together so every page holds the same
    share of the hizb (surah header lines counted as one line of text each)."""
    w = [sum(x for _, x in txt.units(s, a)) + txt.sp * len(txt.units(s, a)) for s, a in ayahs]
    hdr = [header_lines(s) if a == 1 else 0 for s, a in ayahs]
    q = sum(w) / (PAGES_PER_HIZB * LINES - sum(hdr))
    v = np.concatenate([[0], np.cumsum(np.array(w) + np.array(hdr) * q)])
    target = v[-1] / PAGES_PER_HIZB
    n, P, INF = len(ayahs), PAGES_PER_HIZB, 1e30
    best = np.full((P + 1, n + 1), INF)
    back = np.zeros((P + 1, n + 1), int)
    best[0][0] = 0
    for k in range(1, P + 1):
        for i in range(k, n - (P - k) + 1):
            for j in range(max(k - 1, i - 150), i):
                if best[k - 1][j] >= INF:
                    continue
                c = best[k - 1][j] + (v[i] - v[j] - target) ** 2
                if c < best[k][i]:
                    best[k][i], back[k][i] = c, j
    cuts, k = [n], P
    while k:
        cuts.append(back[k][cuts[-1]])
        k -= 1
    cuts = cuts[::-1]
    return [ayahs[a:b] for a, b in zip(cuts[:-1], cuts[1:])]


def lines_needed(ws, width, sp):
    n, cur = 1, -sp
    for w in ws:
        if cur + sp + w <= width:
            cur += sp + w
        else:
            n, cur = n + 1, w
    return n


def flowing_pages(txt, ayahs, W):
    """Juz 30: fill pages in sequence at line width W; a page closes before an
    ayah (with its surah header, if any) that would no longer fit."""
    pages, cur = [], []

    def need(group):
        segs, total = [], 0
        for s, a in group:
            if a == 1 or not segs:
                segs.append([header_lines(s) if a == 1 else 0, []])
            segs[-1][1] += [w for _, w in txt.units(s, a)]
        for h, ws in segs:
            total += h + lines_needed(ws, W, txt.sp)
        return total

    for sa in ayahs:
        if cur and need(cur + [sa]) > LINES:
            pages.append(cur)
            cur = []
        cur.append(sa)
    pages.append(cur)
    return pages, need(pages[-1])


def build_layout(txt, shrink):
    ranges = hizb_ranges()
    book = []  # list of dict(hizb, ayahs, rows)
    for h in range(58):
        a0, a1 = ranges[h]
        for pa in fixed_hizb_pages(txt, txt.flat[a0 - 1:a1 - 1]):
            book.append(dict(hizb=h + 1, ayahs=pa, rows=page_rows(txt, pa)))
    longest = max(r[2] for p in book for r in p["rows"] if r[0] == "text")
    W = longest * (1 - shrink)
    a0, a1 = ranges[58][0], ranges[59][1]
    jz, last_need = flowing_pages(txt, txt.flat[a0 - 1:a1 - 1], W)
    hz60 = ranges[59][0]
    for i, pa in enumerate(jz):
        last = i == len(jz) - 1
        heads = sum(header_lines(s) for s, a in pa if a == 1)
        rows = page_rows(txt, pa, n_lines=(last_need - heads) if last else None)
        idx = txt.flat.index(pa[0]) + 1
        book.append(dict(hizb=59 if idx < hz60 else 60, ayahs=pa, rows=rows))
    return book, W, longest


# --------------------------------------------------------------------- PDF
class PdfPen(BasePen):
    def __init__(self, glyphset):
        super().__init__(glyphset)
        self.ops = []

    def _moveTo(self, p):
        self.ops.append(f"{p[0]:.1f} {p[1]:.1f} m")

    def _lineTo(self, p):
        self.ops.append(f"{p[0]:.1f} {p[1]:.1f} l")

    def _curveToOne(self, a, b, c):
        self.ops.append(f"{a[0]:.1f} {a[1]:.1f} {b[0]:.1f} {b[1]:.1f} {c[0]:.1f} {c[1]:.1f} c")

    def _closePath(self):
        self.ops.append("h")


class Pdf:
    """Minimal PDF writer: each glyph outline is one Form XObject shared by all pages."""

    def __init__(self):
        self.objs = []
        self.pages = []
        self.glyph_obj = {}
        self.sets = {}
        for prefix, path in (("G", FONT_PATH), ("A", LABEL_FONT_PATH)):
            tt = TTFont(path)
            self.sets[prefix] = (tt.getGlyphSet(), tt.getGlyphOrder())
        self.outlines = []  # (title, page_index)

    def add(self, body):
        self.objs.append(body)
        return len(self.objs)

    def stream(self, data, extra=""):
        comp = zlib.compress(data.encode("latin-1"), 9)
        return self.add((f"<< /Length {len(comp)} /Filter /FlateDecode {extra}>>\nstream\n").encode("latin-1")
                        + comp + b"\nendstream")

    def glyph(self, key):
        if key not in self.glyph_obj:
            prefix, gid = key[0], int(key[1:])
            gs, order = self.sets[prefix]
            pen = PdfPen(gs)
            gs[order[gid]].draw(pen)
            ops = " ".join(pen.ops) + (" f" if pen.ops else "")
            self.glyph_obj[key] = self.stream(ops, "/Type /XObject /Subtype /Form /BBox [-3000 -3000 9000 5000] ")
        return self.glyph_obj[key]

    def add_page(self, content, used):
        res = " ".join(f"/{g} {self.glyph(g)} 0 R" for g in sorted(used))
        c = self.stream(content)
        self.pages.append((c, res))

    def save(self, path, title):
        n_pages = len(self.pages)
        base = len(self.objs)
        pages_id = base + 1
        page_ids = [base + 2 + i for i in range(n_pages)]
        bodies = [None]
        kids = " ".join(f"{p} 0 R" for p in page_ids)
        bodies[0] = f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode()
        for c, res in self.pages:
            bodies.append((f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PAGE_W:.2f} {PAGE_H:.2f}] "
                           f"/Resources << /XObject << {res} >> >> /Contents {c} 0 R >>").encode())
        nxt = base + 1 + len(bodies)
        out_root = nxt
        items = self.outlines
        ids = [out_root + 1 + i for i in range(len(items))]
        if ids:
            out_bodies = [f"<< /Type /Outlines /First {ids[0]} 0 R /Last {ids[-1]} 0 R /Count {len(ids)} >>".encode()]
        else:
            out_bodies = [b"<< /Type /Outlines /Count 0 >>"]
        for i, (t, pi) in enumerate(items):
            ttl = "<FEFF" + t.encode("utf-16-be").hex().upper() + ">"
            link = f"/Prev {ids[i-1]} 0 R " if i else ""
            link += f"/Next {ids[i+1]} 0 R " if i < len(ids) - 1 else ""
            out_bodies.append(f"<< /Title {ttl} /Parent {out_root} 0 R {link}/Dest [{page_ids[pi]} 0 R /Fit] >>".encode())
        cat = out_root + len(out_bodies)
        tl = "<FEFF" + title.encode("utf-16-be").hex().upper() + ">"
        info = cat + 1
        tail = [f"<< /Type /Catalog /Pages {pages_id} 0 R /Outlines {out_root} 0 R /PageMode /UseOutlines "
                f"/ViewerPreferences << /Direction /R2L >> >>".encode(),
                f"<< /Title {tl} /Producer (Quran-Nazm render_mushaf.py) >>".encode()]
        allobjs = self.objs + bodies + out_bodies + tail
        with open(path, "wb") as f:
            f.write(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
            offs = []
            for i, body in enumerate(allobjs, 1):
                offs.append(f.tell())
                if isinstance(body, str):
                    body = body.encode()
                f.write(f"{i} 0 obj\n".encode() + body + b"\nendobj\n")
            x = f.tell()
            f.write(f"xref\n0 {len(allobjs)+1}\n0000000000 65535 f \n".encode())
            for o in offs:
                f.write(f"{o:010d} 00000 n \n".encode())
            f.write(f"trailer\n<< /Size {len(allobjs)+1} /Root {cat} 0 R /Info {info} 0 R >>\nstartxref\n{x}\n%%EOF\n".encode())


def rgb(c, stroke=False):
    return f"{c[0]:.3f} {c[1]:.3f} {c[2]:.3f} {'RG' if stroke else 'rg'}"


def rounded_rect(x, y, w, h, r):
    k = 0.5523 * r
    return (f"{x+r:.2f} {y:.2f} m {x+w-r:.2f} {y:.2f} l {x+w-r+k:.2f} {y:.2f} {x+w:.2f} {y+r-k:.2f} {x+w:.2f} {y+r:.2f} c "
            f"{x+w:.2f} {y+h-r:.2f} l {x+w:.2f} {y+h-r+k:.2f} {x+w-r+k:.2f} {y+h:.2f} {x+w-r:.2f} {y+h:.2f} c "
            f"{x+r:.2f} {y+h:.2f} l {x+r-k:.2f} {y+h:.2f} {x:.2f} {y+h-r+k:.2f} {x:.2f} {y+h-r:.2f} c "
            f"{x:.2f} {y+r:.2f} l {x:.2f} {y+r-k:.2f} {x+r-k:.2f} {y:.2f} {x+r:.2f} {y:.2f} c h")


def place(glyphs, x, y, k, xs, used, out, prefix="G"):
    for gid, gx, gy in glyphs:
        if gid == 0:
            continue
        used.add(f"{prefix}{gid}")
        out.append(f"q {k*xs:.5f} 0 0 {k:.5f} {x + k*gx*xs:.2f} {y + k*gy:.2f} cm /{prefix}{gid} Do Q")


def plain(txt, text, font=None):
    buf = J.shape(font or txt.font, text)
    out, x = [], 0
    for i, p in zip(buf.glyph_infos, buf.glyph_positions):
        out.append((i.codepoint, x + p.x_offset, p.y_offset))
        x += p.x_advance
    return out, x


def render_page(pdf, txt, page, number, W, stats):
    k = BLOCK_W / W
    pitch = PITCH_RATIO * W * k
    x0 = (PAGE_W - BLOCK_W) / 2
    top = PAGE_H - (PAGE_H - LINES * pitch) / 2 + 4
    out, used = [], set()
    # frame
    pad = 9
    out.append(f"q {rgb(GREEN, True)} 1.2 w " + rounded_rect(x0 - pad, top - LINES * pitch - pad, BLOCK_W + 2 * pad,
                                                              LINES * pitch + 2 * pad, 6) + " S Q")
    out.append(f"q {rgb(GREEN, True)} 0.4 w " + rounded_rect(x0 - pad + 3, top - LINES * pitch - pad + 3,
                                                              BLOCK_W + 2 * pad - 6, LINES * pitch + 2 * pad - 6, 4) + " S Q")
    # running heads: surah (right), juz and hizb (left), page number (bottom)
    s0 = page["ayahs"][0][0]
    small = k * 0.62
    g, w = plain(txt, txt.suras[s0 - 1]["title"])
    out.append(f"q {rgb(GREEN)}")
    place(g, x0 + BLOCK_W - w * small, top + pad + 10, small, 1.0, used, out)
    label = f"الجزء {ar_num((page['hizb'] + 1) // 2)}   الحزب {ar_num(page['hizb'])}"
    lab = k * 0.55
    g, w = plain(txt, label, txt.label_font)
    place(g, x0, top + pad + 10, lab, 1.0, used, out, "A")
    g, w = plain(txt, ar_num(number), txt.label_font)
    place(g, PAGE_W / 2 - w * lab / 2, top - LINES * pitch - pad - 22, lab, 1.0, used, out, "A")
    out.append("Q")
    out.append(f"q {rgb(INK)}")
    for i, row in enumerate(page["rows"]):
        ytop = top - i * pitch
        base = ytop - BASELINE_IN_ROW * pitch
        if row[0] == "title":
            out.append(f"Q q {rgb(PALE)} {rounded_rect(x0 + 6, ytop - pitch + 5, BLOCK_W - 12, pitch - 10, 5)} f "
                       f"{rgb(GREEN, True)} 0.9 w {rounded_rect(x0 + 6, ytop - pitch + 5, BLOCK_W - 12, pitch - 10, 5)} S Q q {rgb(INK)}")
            g, w = plain(txt, txt.suras[row[1] - 1]["title"])
            s = 0.85 * k
            place(g, x0 + BLOCK_W / 2 - w * s / 2, base + 1, s, 1.0, used, out)
            pdf.outlines.append((txt.suras[row[1] - 1]["title"], len(pdf.pages)))
            continue
        if row[0] == "basmala":
            g, w = plain(txt, txt.basmala)
            place(g, x0 + BLOCK_W / 2 - w * k / 2, base, k, 1.0, used, out)
            continue
        text, nat = " ".join(row[1]), row[2]
        ratio = W / nat
        if ratio > 1.8:  # a few words left over before a surah ends: centre them, do not over-stretch
            target = nat * 1.25
            r = J.justify_line(txt.font, text, target)
            g, x = J.line_glyphs(txt.font, text, r)
            place(g, x0 + BLOCK_W / 2 - x * k / 2, base, k, 1.0, used, out)
            stats["centred"] += 1
            continue
        r = J.justify_line(txt.font, text, W)
        g, x = J.line_glyphs(txt.font, text, r)
        place(g, x0 + BLOCK_W - x * r.x_scale * k, base, k, r.x_scale, used, out)
        stats["ratios"].append(ratio)
        stats["xscale"].append(r.x_scale)
    out.append("Q")
    pdf.add_page("\n".join(out), used)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shrink", type=float, default=0.25, help="largest allowed compression of a line (default 0.25)")
    ap.add_argument("--out", default=os.path.join(WORK, "quran-nazm.pdf"))
    ap.add_argument("--pages", default=None, help="page range to render, e.g. 1-20 (layout is always computed for the whole book)")
    args = ap.parse_args()
    t0 = time.time()
    txt = Text()
    book, W, longest = build_layout(txt, args.shrink)
    print(f"layout: {len(book)} pages, line width {W:.0f} units "
          f"(type {15437.6 / W * 100:.0f}% of Madina 1441H), {time.time() - t0:.0f}s")
    lo, hi = 1, len(book)
    if args.pages:
        lo, hi = (int(x) for x in args.pages.split("-"))
    pdf = Pdf()
    stats = dict(ratios=[], xscale=[], centred=0)
    for n in range(lo, hi + 1):
        render_page(pdf, txt, book[n - 1], n, W, stats)
        if n % 50 == 0:
            print(f"  page {n} ({time.time() - t0:.0f}s)")
    pdf.save(args.out, "Quran-Nazm")
    r, xs = np.array(stats["ratios"]), np.array(stats["xscale"])
    # checks: every page ends on an ayah marker, no line starts with one
    ends_ok = all(p["rows"][-1][0] == "text" and MARK in p["rows"][-1][1][-1] for p in book)
    starts_ok = all(not row[1][0].startswith(MARK) for p in book for row in p["rows"] if row[0] == "text")
    # within_page_spread: median over pages of the standard deviation of log(stretch)
    # across the page's lines (hizbs 1-58); 0.065 is the same measure on the 1441H print.
    rep = dict(pages=len(book), rendered=f"{lo}-{hi}", shrink_limit=args.shrink, line_width_units=round(W),
               type_size_vs_madina=round(15437.6 / W, 3),
               stretch_median=round(float(np.median(r)), 3), stretch_p5=round(float(np.percentile(r, 5)), 3),
               stretch_p95=round(float(np.percentile(r, 95)), 3), stretch_max=round(float(r.max()), 3),
               lines_compressed=round(float((r < 1).mean()), 3), lines_squeezed=round(float((xs < 0.999).mean()), 3),
               squeeze_max=round(float(1 - xs.min()), 3), centred_lines=stats["centred"],
               every_page_ends_on_ayah=ends_ok, no_line_starts_with_marker=starts_ok,
               juz30_pages=sum(1 for p in book if p["hizb"] >= 59),
               within_page_spread=round(float(np.median([np.std(np.log([W / r[2] for r in p["rows"] if r[0] == "text" and W / r[2] <= 1.8]))
                                                         for p in book if p["hizb"] <= 58])), 3),
               within_page_spread_madina_1441h=0.065)
    base = os.path.splitext(args.out)[0]
    json.dump(rep, open(base + "-report.json", "w"), ensure_ascii=False, indent=1)
    json.dump([dict(page=i + 1, hizb=p["hizb"], first=list(p["ayahs"][0]), last=list(p["ayahs"][-1]),
                    rows=[r[:2] if r[0] != "title" else list(r) for r in p["rows"]]) for i, p in enumerate(book)],
              open(base + "-layout.json", "w"), ensure_ascii=False)
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    print(f"wrote {args.out} ({os.path.getsize(args.out) / 1e6:.1f} MB) in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
