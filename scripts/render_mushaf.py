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
from paths import DATA, QMH, ROOT, WORK

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

# Physical page (points). Text block 100 mm wide, 15 rows; row pitch keeps the
# Madina proportion of 0.1086 x line width measured on the 1441H print.
MM = 72 / 25.4
PAGE_W, PAGE_H = 145 * MM, 210 * MM
BLOCK_W = 100 * MM
PITCH_RATIO = 0.1086
BASELINE_IN_ROW = 0.68
INK = (0.09, 0.09, 0.09)
GREEN = (0.18, 0.42, 0.33)
PALE = (0.93, 0.96, 0.94)

# Page frame and surah header art (vector, from quran-ws/quran-assets; see assets/art/*/README.md).
# Each SVG has a transparent "slot" (x, y, w, h in its viewBox) where the text or the
# surah name goes; the art is scaled so that slot fits the text block or the title.
ART_STYLES = {
    "hafs-adi": dict(frame="page-frame.svg", frame_box=(64.419, 100.0), frame_slot=(4.2763, 5.0439, 55.8662, 89.9671),
                     header="surah-header.svg", header_box=(872.674, 100.0), header_slot=(239.8256, 9.593, 393.314, 81.1047)),
}
SLOT_PAD = 1.5 * MM  # white space between the text block and the frame's inner edge

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


def allocate(widths, total, caps, heads=None, mins=None):
    """Share `total` lines among the surah segments of a page: each line goes to the
    segment whose lines are currently the longest on average (so no segment is
    left crowded), never more lines than a segment has words. With `heads` (header
    lines per segment), a line is never given to a segment if that would push a
    later surah title below TITLE_MAX_ROW; `mins` gives each segment's least lines."""
    alloc = list(mins) if mins else [1] * len(widths)

    def fits(i):
        if heads is None:
            return True
        r = 1
        for k, (h, n) in enumerate(zip(heads, alloc)):
            if h and k > i and r > TITLE_MAX_ROW:
                return False
            r += h + n + (1 if k == i else 0)
        return True
    while sum(alloc) < total:
        open_ = [i for i in range(len(widths)) if alloc[i] < caps[i] and fits(i)]
        if not open_:
            break
        i = max(open_, key=lambda i: widths[i] / alloc[i])
        alloc[i] += 1
    return alloc


def page_rows(txt, ayahs, n_lines=None, fit_width=None):
    """Turn the ayahs of one page into rows: ('title', s), ('basmala',), ('text', [unit texts], natural)."""
    segs = []
    for s, a in ayahs:
        if a == 1 or not segs:
            segs.append(dict(s=s, head=(a == 1), units=[]))
        segs[-1]["units"] += txt.units(s, a)
    heads = sum(header_lines(g["s"]) for g in segs if g["head"])
    total = (LINES - heads) if n_lines is None else n_lines
    widths = [sum(w for _, w in g["units"]) + txt.sp * len(g["units"]) for g in segs]
    caps = [len(g["units"]) for g in segs]
    if fit_width:  # title rule enforced by line sharing; each segment keeps the lines it needs
        hs = [header_lines(g["s"]) if g["head"] else 0 for g in segs]
        last_s, last_a = ayahs[-1]
        if TITLE_RULE_EXEMPT_WHOLE and segs[-1]["head"] and last_a == len(txt.suras[last_s - 1]["ayas"]):
            hs[-1] = 0  # the last surah starts and ends on this page: its title may sit lower
        alloc = allocate(widths, total, caps, hs,
                         [lines_needed([w for _, w in g["units"]], fit_width, txt.sp) for g in segs])
    else:
        alloc = allocate(widths, total, caps)
    rows = []
    for g, n in zip(segs, alloc):
        if g["head"]:
            rows.append(("title", g["s"]))
            if header_lines(g["s"]) == 2:
                rows.append(("basmala",))
        ws = [w for _, w in g["units"]]
        for a, b in opt_lines(ws, n, txt.sp):
            nat = sum(ws[a:b]) + txt.sp * (b - a - 1)
            rows.append(("text", [t for t, _ in g["units"][a:b]], nat))
    return rows


TITLE_MAX_ROW = 11  # a surah title may start no lower than this line of the page
TITLE_RULE = True
TITLE_RULE_EXEMPT_WHOLE = False  # juz 30 variant: a surah that ends on the same page may start lower


def title_rows(segs, total=None):
    """Rows (1-based) where the surah titles of a page fall. `segs` lists each surah
    segment of the page as (header lines or 0, natural width, word count), in order;
    lines are shared among segments exactly as page_rows does."""
    heads = sum(h for h, _, _ in segs)
    total = LINES - heads if total is None else total
    alloc = allocate([w for _, w, _ in segs], total, [c for _, _, c in segs])
    rows, r = [], 1
    for (h, _, _), n in zip(segs, alloc):
        if h:
            rows.append(r)
        r += h + n
    return rows


def titles_ok_alloc(heads, alloc):
    r = 1
    for h, n in zip(heads, alloc):
        if h and r > TITLE_MAX_ROW:
            return False
        r += h + n
    return True


def titles_ok(segs):
    return all(r <= TITLE_MAX_ROW for r in title_rows(segs))


def hizb_ranges():
    starts = json.load(open(os.path.join(DATA, "hafs-rub-start-ayahs.json")))
    return [(starts[1 + 4 * h], starts[1 + 4 * h + 4] if h < 59 else 6237) for h in range(60)]


SMALL_SURA_PENALTY = 0.6  # cost of cutting a page inside a surah that fits on one page


def fixed_pages(txt, ayahs, pages, title_rule=True, max_density=None):
    """Cut a run of ayahs into exactly `pages` pages at ayah ends, all cuts chosen
    together so every page holds the same share of text (a surah header counts as
    the lines it uses). Cutting inside a surah short enough to fit on one page is
    penalised, so short surahs stay whole on a page whenever the balance allows."""
    w = [sum(x for _, x in txt.units(s, a)) + txt.sp * len(txt.units(s, a)) for s, a in ayahs]
    hdr = [header_lines(s) if a == 1 else 0 for s, a in ayahs]
    q = sum(w) / (pages * LINES - sum(hdr))
    v = np.concatenate([[0], np.cumsum(np.array(w) + np.array(hdr) * q)])
    target = v[-1] / pages
    # penalty for a cut after ayah i-1 (i.e. at position i) inside a short surah
    span = {}
    for i, (s, a) in enumerate(ayahs):
        span.setdefault(s, [i, i])[1] = i
    pen = np.zeros(len(ayahs) + 1)
    for s, (i0, i1) in span.items():
        whole = ayahs[i0][1] == 1 and ayahs[i1][1] == len(txt.suras[s - 1]["ayas"])
        if whole and v[i1 + 1] - v[i0] <= target:
            pen[i0 + 1:i1 + 1] = SMALL_SURA_PENALTY * target ** 2
    n, P, INF = len(ayahs), pages, 1e30
    cw = np.concatenate([[0], np.cumsum(w)])
    ch = np.concatenate([[0], np.cumsum(hdr)])

    def too_dense(j, i):  # natural text per available line above max_density
        return max_density is not None and (cw[i] - cw[j]) > max_density * (LINES - (ch[i] - ch[j]))
    cnt = [len(txt.units(s, a)) for s, a in ayahs]
    starts = [i for i, (s, a) in enumerate(ayahs) if a == 1]

    def low_title(j, i):  # ayahs j..i-1 on one page put a surah title below TITLE_MAX_ROW
        if not any(j < k < i for k in starts) or not title_rule:
            return False
        segs = []
        for k in range(j, i):
            if k == j or ayahs[k][1] == 1:
                segs.append([hdr[k], 0.0, 0])
            segs[-1][1] += w[k]
            segs[-1][2] += cnt[k]
        return not titles_ok(segs)
    best = np.full((P + 1, n + 1), INF)
    back = np.zeros((P + 1, n + 1), int)
    best[0][0] = 0
    for k in range(1, P + 1):
        for i in range(k, n - (P - k) + 1):
            for j in range(max(k - 1, i - 200), i):
                if best[k - 1][j] >= INF or too_dense(j, i) or low_title(j, i):
                    continue
                c = best[k - 1][j] + (v[i] - v[j] - target) ** 2 + (pen[i] if i < n else 0)
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


# Juz 30: hizb 59 keeps the 10-page rule, hizb 60 (Al-A'la to An-Nas, 28 surahs) is the one exception.
# Both are cut by the lines each page really needs (see juz30_pages), since nearly every page starts a surah.
JUZ30_PAGES = {59: PAGES_PER_HIZB, 60: 14}
MIN_SPLIT_AYAHS = 2      # juz 30: a split surah keeps at least this many ayahs on each page
JUZ30_MAX_STRETCH = 1.35 # juz 30: no page may be sparser than this average stretch (the book's last page excepted under the title rule)
SPLIT_SHORT_SURA = 25.0  # juz 30: cost of splitting a surah that fits on one page (vs. ~0.01 for a typical page)


def juz30_pages(txt, ayahs, pages, W, shrink, max_stretch=None, title_rule=True, last_exempt=True):
    """A hizb of juz 30 on exactly `pages` pages. Its many short surahs each start on a new
    line, so a page is scored by the lines it really needs at width W: every
    surah segment is cut separately, and the page's average stretch should be
    close to 1. A page must fit within the shrink limit; splitting a surah that
    could fit on one page costs far more than any imbalance."""
    n = len(ayahs)
    units = [[w for _, w in txt.units(s, a)] for s, a in ayahs]
    sura_len = {}
    for i, (s, a) in enumerate(ayahs):
        sura_len.setdefault(s, []).append(i)
    small = set()
    for s, idx in sura_len.items():
        ws = [w for i in idx for w in units[i]]
        if header_lines(s) + lines_needed(ws, W, txt.sp) <= LINES:
            small.add(s)
    cap = W / (1 - shrink)

    def page_cost(j, i):  # ayahs j..i-1 on one page
        segs = []
        for k in range(j, i):
            s, a = ayahs[k]
            if a == 1 or not segs:
                segs.append([header_lines(s) if a == 1 else 0, []])
            segs[-1][1] += units[k]
        heads = sum(h for h, _ in segs)
        need = [lines_needed(ws, cap, txt.sp) for _, ws in segs]
        if heads + sum(need) > LINES:
            return None  # cannot fit even at the shrink limit
        avail = LINES - heads
        if avail < len(segs):
            return None
        widths = [sum(ws) + txt.sp * len(ws) for _, ws in segs]
        text = sum(widths)
        stretch = avail * W / text
        if max_stretch and stretch > max_stretch and (i < n or not title_rule or not last_exempt):  # the rule forces 1.50 on the book's last page
            return "sparse"  # too little text: the page would look empty
        if not title_rule:
            return math.log(stretch) ** 2
        hs = [h for h, _ in segs]
        if TITLE_RULE_EXEMPT_WHOLE and hs[-1] and (i == n or ayahs[i][1] == 1):
            hs[-1] = 0  # the last surah starts and ends on this page: its title may sit lower
        alloc = allocate(widths, avail, [len(ws) for _, ws in segs], hs, need)
        if sum(alloc) < avail or not titles_ok_alloc(hs, alloc):
            return "low"  # a surah title would fall below TITLE_MAX_ROW
        # line-weighted mean of log stretch squared, over the page's surah segments
        return sum(n * math.log(n * W / wd) ** 2 for n, wd in zip(alloc, widths)) / avail

    INF = 1e30
    cost = {}
    for j in range(n):
        for i in range(j + 1, min(n, j + 90) + 1):
            c = page_cost(j, i)
            if c is None:
                break
            if c in ("sparse", "low"):
                continue
            if i < n:
                s_prev, s_next = ayahs[i - 1][0], ayahs[i][0]
                if s_prev == s_next:
                    # never leave a surah's header with fewer than 3 ayahs at a page
                    # bottom, nor carry fewer than 3 ayahs over to the next page
                    before = ayahs[i - 1][1]
                    after = len(txt.suras[s_prev - 1]["ayas"]) - before
                    if before < MIN_SPLIT_AYAHS or after < MIN_SPLIT_AYAHS:
                        continue
                    if s_prev in small:
                        c += SPLIT_SHORT_SURA
            cost[j, i] = c
    best = np.full((pages + 1, n + 1), INF)
    back = np.zeros((pages + 1, n + 1), int)
    best[0][0] = 0
    for k in range(1, pages + 1):
        for (j, i), c in cost.items():
            if best[k - 1][j] < INF and best[k - 1][j] + c < best[k][i]:
                best[k][i], back[k][i] = best[k - 1][j] + c, j
    if best[pages][n] >= INF:
        raise SystemExit(f"juz 30 does not fit on {pages} pages within a {shrink:.0%} shrink limit")
    cuts, k = [n], pages
    while k:
        cuts.append(back[k][cuts[-1]])
        k -= 1
    cuts = cuts[::-1]
    return [ayahs[a:b] for a, b in zip(cuts[:-1], cuts[1:])]


def build_layout(txt, shrink):
    ranges = hizb_ranges()
    book = []  # list of dict(hizb, ayahs, rows)
    for h in range(58):
        a0, a1 = ranges[h]
        for pa in fixed_pages(txt, txt.flat[a0 - 1:a1 - 1], PAGES_PER_HIZB, TITLE_RULE):
            book.append(dict(hizb=h + 1, ayahs=pa, rows=page_rows(txt, pa)))
    longest = max(r[2] for p in book for r in p["rows"] if r[0] == "text")
    W = longest * (1 - shrink)
    # Juz 30: hizb 59 on 10 pages like every hizb, hizb 60 the exception; pages scored by lines needed
    for h in (59, 60):
        a0, a1 = ranges[h - 1]
        for pa in juz30_pages(txt, txt.flat[a0 - 1:a1 - 1], JUZ30_PAGES[h], W, shrink, JUZ30_MAX_STRETCH,
                              TITLE_RULE, last_exempt=(h == 60)):
            book.append(dict(hizb=h, ayahs=pa,
                             rows=page_rows(txt, pa, fit_width=W / (1 - shrink) if TITLE_RULE else None)))
    return book, W, longest


def split_short_suras(txt, book):
    """Surahs short enough for one page that still span two pages."""
    pages_of = {}
    for i, p in enumerate(book):
        for s, a in p["ayahs"]:
            pages_of.setdefault(s, set()).add(i)
    out = []
    for s, pg in pages_of.items():
        if len(pg) > 1:
            n = len(txt.suras[s - 1]["ayas"])
            w = sum(x for a in range(1, n + 1) for _, x in txt.units(s, a))
            out.append((s, w))
    return out


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
        self.art = []  # (page_index, 'frame' | 'header', (x0, y0, x1, y1) in PDF points)

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


def star8(cx, cy, r):
    """Eight-pointed star (two overlapping squares), as a filled path."""
    ops = []
    for rot in (0, math.pi / 4):
        pts = [(cx + r * math.cos(rot + i * math.pi / 2), cy + r * math.sin(rot + i * math.pi / 2)) for i in range(4)]
        ops.append(f"{pts[0][0]:.2f} {pts[0][1]:.2f} m " + " ".join(f"{x:.2f} {y:.2f} l" for x, y in pts[1:]) + " h")
    return " ".join(ops)


def circle(cx, cy, r):
    k = 0.5523 * r
    return (f"{cx+r:.2f} {cy:.2f} m {cx+r:.2f} {cy+k:.2f} {cx+k:.2f} {cy+r:.2f} {cx:.2f} {cy+r:.2f} c "
            f"{cx-k:.2f} {cy+r:.2f} {cx-r:.2f} {cy+k:.2f} {cx-r:.2f} {cy:.2f} c "
            f"{cx-r:.2f} {cy-k:.2f} {cx-k:.2f} {cy-r:.2f} {cx:.2f} {cy-r:.2f} c "
            f"{cx+k:.2f} {cy-r:.2f} {cx+r:.2f} {cy-k:.2f} {cx+r:.2f} {cy:.2f} c h")


def cartouche(cx, cy, a, b):
    """Panel with pointed, gently curved ends: half-width a, half-height b."""
    t = b * 1.6
    return (f"{cx-a+t:.2f} {cy+b:.2f} m {cx+a-t:.2f} {cy+b:.2f} l "
            f"{cx+a-t*0.45:.2f} {cy+b:.2f} {cx+a-t*0.2:.2f} {cy+b*0.35:.2f} {cx+a:.2f} {cy:.2f} c "
            f"{cx+a-t*0.2:.2f} {cy-b*0.35:.2f} {cx+a-t*0.45:.2f} {cy-b:.2f} {cx+a-t:.2f} {cy-b:.2f} c "
            f"{cx-a+t:.2f} {cy-b:.2f} l "
            f"{cx-a+t*0.45:.2f} {cy-b:.2f} {cx-a+t*0.2:.2f} {cy-b*0.35:.2f} {cx-a:.2f} {cy:.2f} c "
            f"{cx-a+t*0.2:.2f} {cy+b*0.35:.2f} {cx-a+t*0.45:.2f} {cy+b:.2f} {cx-a+t:.2f} {cy+b:.2f} c h")


def surah_header_art(x0, width, cy, h):
    """Surah header band: a pale ribbon between two fine rules, a central cartouche
    with a double outline for the title, and an eight-pointed star at each end."""
    g, p = rgb(GREEN), rgb(PALE)
    gs = rgb(GREEN, True)
    rib = h * 0.26
    star_r = h * 0.36
    sx1, sx2 = x0 + star_r + 2, x0 + width - star_r - 2
    a, b = width * 0.29, h * 0.42
    cx = x0 + width / 2
    ops = [f"q {p} {sx1:.2f} {cy-rib:.2f} {sx2-sx1:.2f} {2*rib:.2f} re f",
           f"{gs} 0.5 w {sx1:.2f} {cy+rib:.2f} m {sx2:.2f} {cy+rib:.2f} l S {sx1:.2f} {cy-rib:.2f} m {sx2:.2f} {cy-rib:.2f} l S"]
    for d in (-1, 1):  # small diamonds on the ribbon, halfway between star and cartouche
        mx = cx + d * (a + (width / 2 - a - star_r) / 2)
        r = rib * 0.55
        ops.append(f"{g} {mx:.2f} {cy+r:.2f} m {mx+r:.2f} {cy:.2f} l {mx:.2f} {cy-r:.2f} l {mx-r:.2f} {cy:.2f} l h f")
    ops.append(f"{p} {cartouche(cx, cy, a, b)} f {gs} 1.1 w {cartouche(cx, cy, a, b)} S")
    ops.append(f"{gs} 0.45 w {cartouche(cx, cy, a - 2.6, b - 2.6)} S")
    for sx in (sx1, sx2):
        ops.append(f"{g} {star8(sx, cy, star_r)} f {p} {circle(sx, cy, star_r * 0.42)} f {g} {circle(sx, cy, star_r * 0.16)} f")
    ops.append("Q")
    return " ".join(ops)


def justify(font, text, width):
    """Justify one line to `width`.

    Stretching uses the DigitalKhatt rules from quran-madina-html. Compressing
    tightens the spaces (to 60% at most) and then scales the line horizontally.
    The font's word-shrink features (shr1/shrr) are deliberately not used: shaped
    inside a full line they push neighbouring words into each other and squash
    letters within the word (the collisions first seen on page 18)."""
    r = J.justify_line(font, text, width)
    if not r.word_features and r.x_scale >= 1.0:
        return r
    line = J.analyze_line(text)
    sp = J.width(font, " ")
    nat = r.natural_width
    n_simple = sum(1 for t in line.spaces.values() if t == "simple")
    simple, cur = sp, nat
    if n_simple:
        simple = max(sp * J.MIN_SPACE_RATIO, sp - (nat - width) / n_simple)
        cur = nat - (sp - simple) * n_simple
        if cur < width:  # spaces alone were enough: give the remainder back
            simple += (width - cur) / n_simple
            cur = width
    xs = min(1.0, width / cur)
    return J.JustResult({}, simple, sp * J.AYA_SPACE, xs, nat, cur * xs, {})


class FlattenPen(BasePen):
    """Glyph outline as polygons (curves flattened), for rasterising ink."""

    def __init__(self, glyphset, steps=6):
        super().__init__(glyphset)
        self.polys, self.cur, self.steps = [], [], steps

    def _moveTo(self, p):
        self.cur = [p]

    def _lineTo(self, p):
        self.cur.append(p)

    def _curveToOne(self, a, b, c):
        p0 = self.cur[-1]
        for i in range(1, self.steps + 1):
            t = i / self.steps
            u = 1 - t
            self.cur.append((u**3 * p0[0] + 3 * u * u * t * a[0] + 3 * u * t * t * b[0] + t**3 * c[0],
                             u**3 * p0[1] + 3 * u * u * t * a[1] + 3 * u * t * t * b[1] + t**3 * c[1]))

    def _closePath(self):
        if len(self.cur) > 2:
            self.polys.append(self.cur)
        self.cur = []


class InkCheck:
    """Finds neighbouring words whose ink actually touches on a set line.

    Candidates come from glyph boxes that intersect; each candidate pair is then
    rasterised (5 font units per pixel) and counted as a collision only when the
    two words share inked pixels."""

    def __init__(self, font_path, tolerance=30, unit=5, min_pixels=3):
        from fontTools.pens.boundsPen import BoundsPen
        tt = TTFont(font_path)
        self.gs, self.order, self.pen = tt.getGlyphSet(), tt.getGlyphOrder(), BoundsPen
        self.cache, self.polys, self.tol = {}, {}, tolerance
        self.unit, self.min_pixels = unit, min_pixels

    def outline(self, gid):
        if gid not in self.polys:
            pen = FlattenPen(self.gs)
            self.gs[self.order[gid]].draw(pen)
            self.polys[gid] = pen.polys
        return self.polys[gid]

    def ink_overlap(self, g1, g2):
        """Shared inked pixels of two glyph lists [(gid, x, y)] in font units."""
        from PIL import Image, ImageDraw
        pts = [(x + px, y + py) for gid, x, y in g1 + g2 for poly in self.outline(gid) for px, py in poly]
        if not pts:
            return 0
        x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
        x1, y1 = max(p[0] for p in pts), max(p[1] for p in pts)
        size = (int((x1 - x0) / self.unit) + 3, int((y1 - y0) / self.unit) + 3)
        masks = []
        for glyphs in (g1, g2):
            im = Image.new("1", size, 0)
            d = ImageDraw.Draw(im)
            for gid, x, y in glyphs:
                for poly in self.outline(gid):
                    d.polygon([((x + px - x0) / self.unit + 1, (y1 - y - py) / self.unit + 1) for px, py in poly], fill=1)
            masks.append(np.array(im, dtype=bool))
        return int((masks[0] & masks[1]).sum())

    def bounds(self, gid):
        if gid not in self.cache:
            pen = self.pen(self.gs)
            self.gs[self.order[gid]].draw(pen)
            self.cache[gid] = pen.bounds
        return self.cache[gid]

    def collisions(self, font, text, res, extra=None):
        """Pairs of neighbouring words where a glyph of one overlaps a glyph of the
        other in both directions by more than the tolerance. Whole-word boxes are
        not enough: in this hand a descender often tucks under the next word."""
        line = J.analyze_line(text)
        feats = {k: dict(v) for k, v in res.features.items()}
        for wi, wf in res.word_features.items():
            for idx in range(line.words[wi].start, line.words[wi].end + 1):
                feats.setdefault(idx, {}).update(wf)
        buf = J.shape(font, text, J.to_hb_features(feats))
        x, boxes, glyphs = 0.0, {}, {}
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            kind = line.spaces.get(info.cluster)
            adv = (res.aya_spacing if kind == "aya" else res.simple_spacing) if kind else pos.x_advance
            if kind and extra:
                adv += extra.get(info.cluster, 0)
            b = self.bounds(info.codepoint)
            if b and not kind:
                wi = next(k for k, w in enumerate(line.words) if w.start <= info.cluster <= w.end)
                ox, oy = x + pos.x_offset, pos.y_offset
                boxes.setdefault(wi, []).append((ox + b[0], oy + b[1], ox + b[2], oy + b[3]))
                glyphs.setdefault(wi, []).append((info.codepoint, ox, oy))
            x += adv
        out = []
        for w1 in boxes:
            w2 = w1 + 1
            if w2 not in boxes:
                continue
            worst = 0
            for a in boxes[w1]:
                for c in boxes[w2]:
                    ix = min(a[2], c[2]) - max(a[0], c[0])
                    iy = min(a[3], c[3]) - max(a[1], c[1])
                    if ix > self.tol and iy > self.tol:
                        worst = max(worst, min(ix, iy))
            if worst:
                shared = self.ink_overlap(glyphs[w1], glyphs[w2])
                if shared >= self.min_pixels:
                    out.append((line.words[w1].text, line.words[w2].text, shared, line.words[w1].end + 1))
        return out


def line_glyphs(font, text, res, extra=None):
    """As justify.line_glyphs, plus an optional extra advance for individual
    spaces (keyed by the space's character index), used to clear collisions."""
    line = J.analyze_line(text)
    feats = {k: dict(v) for k, v in res.features.items()}
    buf = J.shape(font, text, J.to_hb_features(feats))
    out, x = [], 0.0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        kind = line.spaces.get(info.cluster)
        adv = (res.aya_spacing if kind == "aya" else res.simple_spacing) if kind else pos.x_advance
        if kind and extra:
            adv += extra.get(info.cluster, 0)
        out.append((info.codepoint, x + pos.x_offset, pos.y_offset))
        x += adv
    return out, x


def clear_collisions(ink, font, text, res, step=40, tries=8):
    """Widen only the spaces where neighbouring words touch, step by step; the
    line is then rescaled to its width. Returns (extra, collisions_left)."""
    extra = {}
    for _ in range(tries):
        hits = ink.collisions(font, text, res, extra)
        if not hits:
            return extra, []
        for *_, space in hits:
            extra[space] = extra.get(space, 0) + step
    return extra, ink.collisions(font, text, res, extra)


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
    art = ART_STYLES.get(stats.get("art"))
    bottom = top - LINES * pitch
    if art:
        # quran-assets frame: its slot is stretched over the text block plus a small pad
        fw, fh = art["frame_box"]
        sx0, sy0, sw, sh = art["frame_slot"]
        kx = (BLOCK_W + 2 * SLOT_PAD) / sw
        ky = (LINES * pitch + 2 * SLOT_PAD) / sh
        fx0 = x0 - SLOT_PAD - sx0 * kx
        ftop = top + SLOT_PAD + sy0 * ky
        frame = (fx0, ftop - fh * ky, fx0 + fw * kx, ftop)
        pdf.art.append((len(pdf.pages), "frame", frame))
        head_y, foot_y = frame[3] + 2.6 * MM, frame[1] - 6.0 * MM
    else:
        pad = 9
        out.append(f"q {rgb(GREEN, True)} 1.2 w " + rounded_rect(x0 - pad, bottom - pad, BLOCK_W + 2 * pad,
                                                                  LINES * pitch + 2 * pad, 6) + " S Q")
        out.append(f"q {rgb(GREEN, True)} 0.4 w " + rounded_rect(x0 - pad + 3, bottom - pad + 3,
                                                                  BLOCK_W + 2 * pad - 6, LINES * pitch + 2 * pad - 6, 4) + " S Q")
        head_y, foot_y = top + pad + 10, bottom - pad - 22
    # running heads: surah (right), juz and hizb (left), page number (bottom)
    s0 = page["ayahs"][0][0]
    small = k * 0.62
    g, w = plain(txt, txt.suras[s0 - 1]["title"])
    out.append(f"q {rgb(GREEN)}")
    place(g, x0 + BLOCK_W - w * small, head_y, small, 1.0, used, out)
    label = f"الجزء {ar_num((page['hizb'] + 1) // 2)}   الحزب {ar_num(page['hizb'])}"
    lab = k * 0.55
    g, w = plain(txt, label, txt.label_font)
    place(g, x0, head_y, lab, 1.0, used, out, "A")
    g, w = plain(txt, ar_num(number), txt.label_font)
    place(g, PAGE_W / 2 - w * lab / 2, foot_y, lab, 1.0, used, out, "A")
    out.append("Q")
    out.append(f"q {rgb(INK)}")
    for i, row in enumerate(page["rows"]):
        ytop = top - i * pitch
        base = ytop - BASELINE_IN_ROW * pitch
        if row[0] == "title":
            g, w = plain(txt, txt.suras[row[1] - 1]["title"])
            s = 0.8 * k
            if art:
                bw, bh = art["header_box"]
                hh = 0.96 * pitch
                hw = min(BLOCK_W, hh * bw / bh)
                hx = x0 + (BLOCK_W - hw) / 2
                cy = ytop - pitch / 2
                pdf.art.append((len(pdf.pages), "header", (hx, cy - hh / 2, hx + hw, cy + hh / 2)))
                s = min(s, 0.86 * art["header_slot"][2] / bw * hw / w)  # keep the name inside the slot
            else:
                out.append("Q " + surah_header_art(x0, BLOCK_W, ytop - pitch / 2, pitch) + f" q {rgb(INK)}")
            place(g, x0 + BLOCK_W / 2 - w * s / 2, ytop - pitch / 2 - 0.22 * pitch, s, 1.0, used, out)
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
            r = justify(txt.font, text, target)
            g, x = J.line_glyphs(txt.font, text, r)
            place(g, x0 + BLOCK_W / 2 - x * k / 2, base, k, 1.0, used, out)
            stats["centred"] += 1
            continue
        r = justify(txt.font, text, W)
        extra, left = clear_collisions(stats["ink"], txt.font, text, r)
        g, x = line_glyphs(txt.font, text, r, extra)
        xs = r.x_scale * (W / (x * r.x_scale)) if extra else r.x_scale  # absorb widened spaces
        if extra:
            stats["cleared"] += 1
        for c in left:
            stats["collisions"].append(dict(page=number, line=i + 1, words=list(c[:2]), overlap=c[2]))
        place(g, x0 + BLOCK_W - x * xs * k, base, k, xs, used, out)
        r.x_scale = xs
        stats["ratios"].append(ratio)
        stats["xscale"].append(r.x_scale)
    out.append("Q")
    pdf.add_page("\n".join(out), used)


def apply_art(path, records, style):
    """Lay the quran-assets SVG frame and surah headers under the text of the
    finished PDF. Each SVG is converted to PDF once and placed as a form object."""
    import pymupdf
    art = ART_STYLES[style]
    base = os.path.join(ROOT, "assets", "art", style)
    src = {}
    for kind in ("frame", "header"):
        svg = pymupdf.open(os.path.join(base, art[kind]))
        src[kind] = pymupdf.open("pdf", svg.convert_to_pdf())
    doc = pymupdf.open(path)
    for page_index, kind, (x0, y0, x1, y1) in records:
        page = doc[page_index]
        rect = pymupdf.Rect(x0, PAGE_H - y1, x1, PAGE_H - y0)
        page.show_pdf_page(rect, src[kind], 0, keep_proportion=False, overlay=False)
    tmp = path + ".tmp"
    doc.save(tmp, garbage=3, deflate=True)
    doc.close()
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shrink", type=float, default=0.25, help="largest allowed compression of a line (default 0.25)")
    ap.add_argument("--out", default=os.path.join(WORK, "quran-nazm.pdf"))
    ap.add_argument("--art", default="hafs-adi", choices=sorted(ART_STYLES) + ["none"],
                    help="page frame and surah header art from assets/art (default hafs-adi; 'none' draws the built-in vector art)")
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
    stats = dict(ratios=[], xscale=[], centred=0, collisions=[], cleared=0, ink=InkCheck(FONT_PATH),
                 art=None if args.art == "none" else args.art)
    for n in range(lo, hi + 1):
        render_page(pdf, txt, book[n - 1], n, W, stats)
        if n % 50 == 0:
            print(f"  page {n} ({time.time() - t0:.0f}s)")
    pdf.save(args.out, "Quran-Nazm")
    if args.art != "none":
        apply_art(args.out, pdf.art, args.art)
    r, xs = np.array(stats["ratios"]), np.array(stats["xscale"])
    # checks: every page ends on an ayah marker, no line starts with one
    ends_ok = all(p["rows"][-1][0] == "text" and MARK in p["rows"][-1][1][-1] for p in book)
    starts_ok = all(not row[1][0].startswith(MARK) for p in book for row in p["rows"] if row[0] == "text")
    # within_page_spread: median over pages of the standard deviation of log(stretch)
    # across the page's lines (hizbs 1-58); 0.063 is the same measure on the 1441H print
    # (pages with at least 10 full lines, as in the paper).
    rep = dict(pages=len(book), rendered=f"{lo}-{hi}", shrink_limit=args.shrink, line_width_units=round(W),
               type_size_vs_madina=round(15437.6 / W, 3),
               stretch_median=round(float(np.median(r)), 3), stretch_p5=round(float(np.percentile(r, 5)), 3),
               stretch_p95=round(float(np.percentile(r, 95)), 3), stretch_max=round(float(r.max()), 3),
               lines_compressed=round(float((r < 1).mean()), 3), lines_squeezed=round(float((xs < 0.999).mean()), 3),
               squeeze_max=round(float(1 - xs.min()), 3), centred_lines=stats["centred"],
               every_page_ends_on_ayah=ends_ok, no_line_starts_with_marker=starts_ok,
               lowest_surah_title_row=max(i + 1 for p in book for i, row in enumerate(p["rows"]) if row[0] == "title"),
               juz30_pages=sum(1 for p in book if p["hizb"] >= 59), hizb60_pages=sum(1 for p in book if p["hizb"] == 60),
               short_suras_split=[sn for sn, w in split_short_suras(txt, book)
                                  if header_lines(sn) + lines_needed([x for a in range(1, len(txt.suras[sn - 1]["ayas"]) + 1)
                                                                      for _, x in txt.units(sn, a)], W, txt.sp) <= LINES],
               within_page_spread=round(float(np.median([np.std(np.log([W / r[2] for r in p["rows"] if r[0] == "text" and W / r[2] <= 1.8]))
                                                         for p in book if p["hizb"] <= 58])), 3),
               within_page_spread_madina_1441h=0.063,
               collisions_cleared_by_spacing=stats["cleared"],
               word_collisions=len(stats["collisions"]),
               word_collision_examples=stats["collisions"][:10])
    base = os.path.splitext(args.out)[0]
    json.dump(rep, open(base + "-report.json", "w"), ensure_ascii=False, indent=1)
    json.dump([dict(page=i + 1, hizb=p["hizb"], first=list(p["ayahs"][0]), last=list(p["ayahs"][-1]),
                    rows=[r[:2] if r[0] != "title" else list(r) for r in p["rows"]]) for i, p in enumerate(book)],
              open(base + "-layout.json", "w"), ensure_ascii=False)
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    print(f"wrote {args.out} ({os.path.getsize(args.out) / 1e6:.1f} MB) in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
