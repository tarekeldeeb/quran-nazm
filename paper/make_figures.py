"""Build the figures of the Quran-Nazm paper from the repository data.

    python paper/make_figures.py

Inputs: data/*.json (measurements), figures/*.png (Madina print crops),
output/quran-nazm.pdf (the Nazm render). Outputs go to paper/figures/.
"""
import io
import sys
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
from PIL import Image
import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "figures")
os.makedirs(OUT, exist_ok=True)

GREEN, CORAL, GREY, INK = "#2F6B55", "#C2412D", "#9AA59F", "#1B2420"


def find_font(names):
    """First installed font file whose name matches, in order of preference."""
    files = font_manager.findSystemFonts() + font_manager.findSystemFonts(
        fontpaths=["/usr/share/texmf/fonts/opentype", "/usr/share/texlive/texmf-dist/fonts/opentype"])
    for name in names:
        for f in files:
            if os.path.basename(f).lower() == name.lower():
                return f
    return None


# Charts use the body face of the ACM template (Linux Libertine); TeX Gyre Termes as fallback.
TEXT_FONT = find_font(["LinLibertine_R.otf", "texgyretermes-regular.otf"])
for name in ("LinLibertine_R.otf", "LinLibertine_RB.otf", "texgyretermes-regular.otf", "texgyretermes-bold.otf"):
    f = find_font([name])
    if f:
        font_manager.fontManager.addfont(f)
FAMILY = font_manager.FontProperties(fname=TEXT_FONT).get_name() if TEXT_FONT else "serif"
plt.rcParams.update({
    "font.family": FAMILY, "font.size": 8.5, "axes.titlesize": 9,
    "axes.labelsize": 8.5, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#555",
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "legend.frameon": False, "legend.fontsize": 7.5, "pdf.fonttype": 42,
})
W1 = 3.35  # one column, inches


def data(name):
    return json.load(open(os.path.join(ROOT, "data", name)))


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print("figure:", name)


# 1. Natural length of every full line of the Madina 1441H print
m = [o for o in data("m_1441H.json") if o["full"]]
ratio = np.array([o["ratio"] for o in m])
fig, ax = plt.subplots(figsize=(W1, 1.75))
bins = np.arange(0.6, 1.42, 0.02)
n, b, patches = ax.hist(ratio, bins=bins, color=GREY, edgecolor="white", linewidth=0.4)
for p, left in zip(patches, b[:-1]):
    c = left + 0.01
    if c > 1.10:
        p.set_facecolor(CORAL)
    elif c < 0.90:
        p.set_facecolor(GREEN)
ax.axvline(1.0, color=INK, lw=0.7, ls=(0, (3, 2)))
ax.set_xlabel("natural length of the line ÷ fixed line width")
ax.set_ylabel("lines")
ax.set_xticks([0.6, 0.8, 1.0, 1.2, 1.4], ["60%", "80%", "100%", "120%", "140%"])
ax.text(0.62, n.max() * 0.85, f"{(ratio < 0.9).mean()*100:.0f}% too short\n(stretched)", color=GREEN, fontsize=7)
ax.text(1.18, n.max() * 0.85, f"{(ratio > 1.1).mean()*100:.0f}% too long\n(compressed)", color=CORAL, fontsize=7)
save(fig, "fig_density.pdf")

# 2. Pen width and ink per letter by crowding (scan of the 1441H print)
w = [o for o in data("w_1441H.json") if o.get("full")]
r = np.array([o["ratio"] for o in w])
sw = np.array([o["sw"] for o in w])
ipl = np.array([o["ink"] / o["letters"] for o in w])
edges = [(0.6, 0.8), (0.8, 0.9), (0.9, 1.0), (1.0, 1.1), (1.1, 1.2), (1.2, 1.4)]
labels = ["<80", "80–90", "90–100", "100–110", "110–120", ">120"]
msw = [sw[(r >= a) & (r < c)].mean() for a, c in edges]
mipl = [ipl[(r >= a) & (r < c)].mean() for a, c in edges]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(W1, 1.6))
cols = [GREEN] + [GREY] * 4 + [CORAL]
a1.bar(range(6), msw, color=cols, width=0.7)
a1.set_ylim(2.1, 2.36)
a1.set_title("pen width (px)", loc="left")
a2.bar(range(6), mipl, color=cols, width=0.7)
a2.set_ylim(90, 135)
a2.set_title("ink per letter (px²)", loc="left")
for ax in (a1, a2):
    ax.set_xticks(range(6), labels, rotation=45, ha="right")
    ax.set_xlabel("natural length (%)")
fig.tight_layout(w_pad=1.2)
save(fig, "fig_weight.pdf")

# 3. Natural length of the 60 hizbs
pg = np.array(data("hist60.json")["pg"])
fig, ax = plt.subplots(figsize=(W1, 1.55))
bins = np.arange(8.0, 12.01, 0.25)
ax.hist([pg[:58], pg[58:]], bins=bins, stacked=True, color=[GREEN, GREY], edgecolor="white", linewidth=0.4,
        label=["hizbs 1–58", "juz 30 (hizbs 59–60)"])
ax.axvline(10, color=INK, lw=0.7, ls=(0, (3, 2)))
ax.text(9.95, 12.2, "10 pages", fontsize=7, ha="right")
ax.set_ylim(0, 13)
ax.set_yticks([0, 3, 6, 9])
ax.set_xlabel("natural length of the hizb, in Madina-size pages")
ax.set_ylabel("hizbs")
ax.legend(loc="upper right", ncol=1, bbox_to_anchor=(1.0, 1.02))
save(fig, "fig_hizb.pdf")

# 3b. Length of rub', half hizb, hizb and juz relative to their mean (the root variance)
T = np.array([o["T"] for o in data("rub_minmax.json")])
fig, ax = plt.subplots(figsize=(W1, 1.65))
units = [(1, "rub'\n(240)"), (2, "half hizb\n(120)"), (4, "hizb\n(60)"), (8, "juz\n(30)")]
rng = np.random.default_rng(1)
for k, (n, lab) in enumerate(units):
    g = np.array([T[i:i + n].sum() for i in range(0, 240, n)])
    v = g / g.mean()
    y = k + rng.uniform(-0.18, 0.18, len(v))
    ax.scatter(v, y, s=4 if n < 4 else 7, color=GREEN if n in (4, 8) else GREY, linewidths=0)
    ax.plot([v.min(), v.max()], [k + 0.32, k + 0.32], color=INK, lw=0.6)
    ax.text(v.max() + 0.02, k + 0.32, f"{v.max() / v.min():.2f}×  (cv {g.std() / g.mean():.3f})",
            va="center", fontsize=6.5)
ax.set_yticks(range(4), [u[1] for u in units])
ax.invert_yaxis()
ax.axvline(1.0, color=INK, lw=0.6, ls=(0, (3, 2)))
ax.set_xlim(0.55, 1.95)
ax.set_xlabel("length of the unit ÷ mean length of its kind")
ax.spines["left"].set_visible(False)
ax.tick_params(axis="y", length=0)
save(fig, "fig_units.pdf")

# 4. Line stretch: Madina 1441H vs Nazm (all lines, and spread inside each page)
mad_pages = {}  # juz 1-29 only (juz 30 starts on page 582 of the print), as in the unit comparison
for o in m:
    if o["p"] < 582:
        mad_pages.setdefault(o["p"], []).append(1 / o["ratio"])
nz = data("nazm_line_stretch.json")["pages"]
nz_lines = np.array([s for p in nz if p["juz"] <= 29 for s in p["stretch"] if s <= 1.8])
mad_lines = np.array([v for vs in mad_pages.values() for v in vs])
fig, (a1, a2) = plt.subplots(1, 2, figsize=(W1, 1.7))
bins = np.arange(0.6, 1.8, 0.03)
a1.hist(mad_lines, bins=bins, color=CORAL, alpha=0.55, label="Madina 1441H", density=True)
a1.hist(nz_lines, bins=bins, color=GREEN, alpha=0.65, label="Nazm", density=True)
a1.set_xlabel("stretch applied to a line")
a1.set_yticks([])
a1.set_title("all lines", loc="left")
sd_m = [np.std(np.log(v)) for v in mad_pages.values() if len(v) >= 10]
sd_n = [np.std(np.log([s for s in p["stretch"] if s <= 1.8])) for p in nz if p["juz"] <= 29]
bins = np.arange(0, 0.2, 0.006)
a2.hist(sd_m, bins=bins, color=CORAL, alpha=0.55, density=True)
a2.hist(sd_n, bins=bins, color=GREEN, alpha=0.65, density=True)
a2.axvline(np.median(sd_m), color=CORAL, lw=0.8)
a2.axvline(np.median(sd_n), color=GREEN, lw=0.8)
a2.set_xlabel("spread of stretch within a page")
a2.set_yticks([])
a2.set_title("inside each page", loc="left")
fig.tight_layout(w_pad=1.0, rect=(0, 0, 1, 0.88))
h, l = a1.get_legend_handles_labels()
fig.legend(h, l, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.0))
save(fig, "fig_stretch.pdf")
print(f"medians: Madina {np.median(sd_m):.3f}, Nazm {np.median(sd_n):.3f}")

# 4b. Mean stretch of each juz in the final layout (the variance left between juz)
jd = data("juz_design.json")
pj = np.array(jd["per_juz_mean_stretch"])
fig, ax = plt.subplots(figsize=(W1, 1.45))
cols = [CORAL if v == pj.max() or v == pj.min() else GREEN for v in pj]
ax.bar(np.arange(1, len(pj) + 1), pj, color=cols, width=0.72)
ax.axhline(1.0, color=INK, lw=0.6, ls=(0, (3, 2)))
ax.set_ylim(0.9, pj.max() + 0.06)
jmax, jmin = int(np.argmax(pj)) + 1, int(np.argmin(pj)) + 1
for jj in (jmax, jmin):
    ax.text(jj + (0.35 if jj == len(pj) else 0), pj[jj - 1] + 0.008, f"juz {jj}", ha="center", fontsize=6, color=CORAL)
ax.set_xlim(0.2, len(pj) + 1.2)
ax.set_xlabel("juz")
ax.set_ylabel("mean stretch")
ax.set_xticks([1, 5, 10, 15, 20, 25, 29])
save(fig, "fig_juz_stretch.pdf")

# 4d. Where the variance sits: Madina vs 10 pages per hizb vs 20 pages per juz
uc = data("unit_comparison.json")
layouts = [("madina_1441h", "Madina 1441H", CORAL), ("nazm_hizb", "Nazm, 10 pages/hizb", GREY),
           ("nazm_juz", "Nazm, 20 pages/juz", GREEN)]
parts = [("sd_log_stretch", "all lines"), ("sd_between_juz", "between\njuz"),
         ("sd_between_pages_in_juz", "between pages\nof a juz"), ("sd_within_page", "within\na page")]
fig, ax = plt.subplots(figsize=(W1, 1.75))
x = np.arange(len(parts))
for k, (key, lab, col) in enumerate(layouts):
    v = [uc[key][q] for q, _ in parts]
    ax.bar(x + (k - 1) * 0.26, v, width=0.25, color=col, label=lab)
    for xi, vi in zip(x + (k - 1) * 0.26, v):
        ax.text(xi, vi + 0.002, f"{vi:.3f}".lstrip("0"), ha="center", fontsize=5.2, rotation=90, va="bottom")
ax.set_xticks(x, [lab for _, lab in parts])
ax.set_ylabel("s.d. of log stretch")
ax.set_ylim(0, 0.125)
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, fontsize=6.2, frameon=False,
          handlelength=1.0, columnspacing=0.9)
save(fig, "fig_variance.pdf")

# 4c. Average pen width of every all-text page of the scan (page-level drift)
pages_sw = {}
for o in data("w_1441H.json"):
    pages_sw.setdefault(o["p"], []).append(o["sw"])
pn = np.array(sorted(pages_sw))
pw = np.array([np.mean(pages_sw[p]) for p in pn])
fig, ax = plt.subplots(figsize=(W1, 1.45))
ax.scatter(pn, pw, s=2.5, color=GREY, linewidths=0)
for p_, lab in ((561, "p. 561"), (563, "p. 563")):
    i = int(np.where(pn == p_)[0][0])
    ax.scatter([p_], [pw[i]], s=12, color=CORAL if p_ == 561 else GREEN, zorder=3)
    ax.annotate(lab, (p_, pw[i]), xytext=(-24, 4 if p_ == 561 else -9), textcoords="offset points", fontsize=6.5)
ax.set_xlabel("page of the print")
ax.set_ylabel("pen width (px)")
save(fig, "fig_page_drift.pdf")

# 5. Pages of the Nazm render as vector PDF pages, and crops of the Madina print
src = pymupdf.open(os.path.join(ROOT, "output", "quran-nazm.pdf"))
import pypdf  # noqa: E402  (decodes the PDF's Arabic page labels)
by_label = {lab: i for i, lab in enumerate(pypdf.PdfReader(os.path.join(ROOT, "output", "quran-nazm.pdf")).page_labels)}
fig_pages = data("paper_pages.json")  # page labels used by the paper, chosen from the layout
names = {"ا": "alef", "ب": "beh"}
for lab in sorted(set(fig_pages.values())):
    one = pymupdf.open()
    one.insert_pdf(src, from_page=by_label[lab], to_page=by_label[lab])
    name = f"nazm-{names[lab]}.pdf" if lab in names else f"nazm-p{int(lab):03d}.pdf"
    one.save(os.path.join(OUT, name))
    print("figure:", name)
# 5b. The print's page 156 inside the same Hafs frame as the Nazm pages, for a fair side-by-side view:
# the text block of the scan is placed where Nazm's text block sits, under the same quran-assets frame.
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import render_mushaf as RM  # noqa: E402
art = RM.ART_STYLES["hafs-adi"]
pitch = RM.PITCH_RATIO * RM.BLOCK_W
x0 = (RM.PAGE_W - RM.BLOCK_W) / 2
top = RM.PAGE_H - (RM.PAGE_H - RM.LINES * pitch) / 2 + 4
fw, fh = art["frame_box"]
sx0, sy0, sw, sh = art["frame_slot"]
kx = (RM.BLOCK_W + 2 * RM.SLOT_PAD) / sw
ky = (RM.LINES * pitch + 2 * RM.SLOT_PAD) / sh
fx0 = x0 - RM.SLOT_PAD - sx0 * kx
ftop = top + RM.SLOT_PAD + sy0 * ky
H = RM.PAGE_H
doc = pymupdf.open()
pg = doc.new_page(width=RM.PAGE_W, height=H)
frame = pymupdf.open("pdf", pymupdf.open(os.path.join(ROOT, "assets", "art", "hafs-adi", art["frame"])).convert_to_pdf())
pg.show_pdf_page(pymupdf.Rect(fx0, H - ftop, fx0 + fw * kx, H - (ftop - fh * ky)), frame, 0, keep_proportion=False)
scan = Image.open(os.path.join(ROOT, "figures", "01-1441h-page-156.png")).convert("RGB")
scan = scan.crop((7, 7, scan.width - 7, scan.height - 7))  # drop the scan's own thin rule
buf = io.BytesIO()
scan.save(buf, format="PNG")
pg.insert_image(pymupdf.Rect(x0, H - top, x0 + RM.BLOCK_W, H - (top - RM.LINES * pitch)), stream=buf.getvalue(),
                 keep_proportion=False)
doc.save(os.path.join(OUT, "madina-p156-framed.pdf"))
print("figure: madina-p156-framed.pdf")
for name in ("01-1441h-page-156.png", "02-p-102-line-4.png", "03-p-102-line-5.png",
             "04-p-561-line-9.png", "05-p-563-line-9.png", "06-p-192-line-1-10-words.png",
             "07-p-192-line-14-5-words.png", "08-p-567-lines-2-3-ayah-marker-split.png"):
    with open(os.path.join(ROOT, "figures", name), "rb") as f, open(os.path.join(OUT, "madina-" + name), "wb") as g:
        g.write(f.read())
    print("figure:", "madina-" + name)

# 6. Page 156 of the 1441H print set at natural length (needs quran-madina-html, see paths.py)
import sys
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from paths import QMH, WORK  # noqa: E402
sys.path.insert(0, os.path.join(QMH, "src", "db", "v2"))
import uharfbuzz as hb  # noqa: E402
import justify as J  # noqa: E402
from fontTools.pens.svgPathPen import SVGPathPen  # noqa: E402
from fontTools.pens.transformPen import TransformPen  # noqa: E402
from fontTools.ttLib import TTFont  # noqa: E402


class GlyphPaths:
    """SVG path data for glyph ids of one font (y axis flipped), cached."""

    def __init__(self, path):
        tt = TTFont(path)
        self.gs, self.order, self.cache = tt.getGlyphSet(), tt.getGlyphOrder(), {}

    def path(self, gid):
        if gid not in self.cache:
            pen = SVGPathPen(self.gs)
            self.gs[self.order[gid]].draw(TransformPen(pen, (1, 0, 0, -1, 0, 0)))
            self.cache[gid] = pen.getCommands()
        return self.cache[gid]


font_path = os.path.join(WORK, "madina.otf")
font = hb.Font(hb.Face(open(font_path, "rb").read()))
paths = GlyphPaths(font_path)
LW = 15437.6
lines = sorted([o for o in m if o["p"] == 156], key=lambda o: o["l"])
pitch, left, right = 2300, -4400, LW + 3300
parts, labels = [], []
for i, o in enumerate(lines):
    buf = J.shape(font, o["text"])
    x, glyphs = 0, []
    for inf, pos in zip(buf.glyph_infos, buf.glyph_positions):
        glyphs.append((inf.codepoint, x + pos.x_offset, pos.y_offset))
        x += pos.x_advance
    y = i * pitch + 1500
    x0 = LW - x
    if x > LW:
        parts.append(f'<rect x="{x0:.0f}" y="{y-1250}" width="{x-LW:.0f}" height="{pitch-300}" fill="#F3D2CA"/>')
    else:
        parts.append(f'<rect x="0" y="{y-1250}" width="{LW-x:.0f}" height="{pitch-300}" fill="#DCEBE3"/>')
    for gid, gx, gy in glyphs:
        d = paths.path(gid)
        if d:
            parts.append(f'<path transform="translate({x0+gx:.0f} {y-gy:.0f})" d="{d}" fill="#1B2420"/>')
    pct = (x / LW - 1) * 100
    col = "#C2412D" if pct > 10 else "#2F6B55" if pct < -10 else "#6B756F"
    labels.append((LW + 380, y - 150, f'{"+" if pct >= 0 else "−"}{abs(pct):.0f}%', col))
H = len(lines) * pitch + 300
for xline in (0, LW):
    parts.append(f'<line x1="{xline}" y1="0" x2="{xline}" y2="{H}" stroke="#2F6B55" stroke-width="45" stroke-dasharray="170 120"/>')
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{left} 0 {right-left} {H}" '
       f'width="{(right-left)/60:.0f}" height="{H/60:.0f}">' + "".join(parts) + "</svg>")
doc = pymupdf.open(stream=svg.encode(), filetype="svg")
fig = pymupdf.open("pdf", doc.convert_to_pdf())
# percentage labels are drawn afterwards with an embedded copy of the text face,
# so the figure carries no unembedded fonts (required by ACM and IEEE)
page = fig[0]
page.insert_font(fontname="label", fontfile=TEXT_FONT)
sx = page.rect.width / (right - left)
for x_u, y_u, label, col in labels:
    page.insert_text(((x_u - left) * sx, y_u * sx), label, fontname="label", fontsize=720 * sx,
                     color=tuple(int(col[i:i + 2], 16) / 255 for i in (1, 3, 5)))
fig.save(os.path.join(OUT, "fig_p156_natural.pdf"), garbage=3, deflate=True)
print("figure: fig_p156_natural.pdf")
