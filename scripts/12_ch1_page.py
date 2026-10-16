"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import json
P=json.load(open(WORK+'/parts.json'));s=P['stats']
html=f'''<title>Quran-Nazm Evidence</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500&family=IBM+Plex+Sans:wght@400;500&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: one reading column; full-page specimens scroll sideways inside their own frames */
:root{{--bg:#F3F5F2;--panel:#FFFFFF;--ink:#16201B;--muted:#5D6B63;--rule:#D3DBD5;--frame:#2F6B55;--over:#C2412D;--overbg:#F6D9D2;--slack:#E3ECE6;
--display:"Newsreader",Georgia,serif;--body:"IBM Plex Sans",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,monospace}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#111714;--panel:#18201C;--ink:#E6ECE8;--muted:#9AAAA1;--rule:#2C3832;--frame:#6FBF9F;--over:#F07A62;--overbg:#4A2620;--slack:#1F2B25;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#111714;--panel:#18201C;--ink:#E6ECE8;--muted:#9AAAA1;--rule:#2C3832;--frame:#6FBF9F;--over:#F07A62;--overbg:#4A2620;--slack:#1F2B25;color-scheme:dark}}
body{{background:var(--bg);color:var(--ink);font:400 16px/1.65 var(--body)}}
main{{max-width:880px;margin:0 auto;padding-block:40px 64px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:grid;gap:44px}}
h1{{font:500 clamp(30px,6vw,46px)/1.1 var(--display);margin:0;text-wrap:balance}}
h2{{font:500 26px/1.2 var(--display);margin:0;text-wrap:balance}}
p{{margin:0;max-width:66ch}} section{{display:grid;gap:16px;min-width:0}}
.eyebrow{{font:500 12px var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--frame)}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}}
.stat{{background:var(--panel);border:1px solid var(--rule);border-radius:6px;padding:14px 16px}}
.stat b{{display:block;font:500 30px/1.1 var(--display)}} .stat span{{font-size:13px;color:var(--muted)}}
.spec{{background:var(--panel);border:1px solid var(--rule);border-radius:6px;padding:16px 12px;overflow-x:auto}}
.spec svg.pg{{display:block;min-width:620px;width:100%;height:auto}}
.ink{{fill:var(--ink)}} .edge{{stroke:var(--frame);stroke-width:40;stroke-dasharray:160 120}}
.over{{fill:var(--overbg)}} .slack{{fill:var(--slack)}}
.lab{{font:500 640px var(--mono);fill:var(--muted)}} .lab.hi{{fill:var(--over)}} .lab.lo{{fill:var(--frame)}} .lab2{{font:400 520px var(--mono);fill:var(--muted)}}
.cap{{font-size:14px;color:var(--muted);max-width:66ch}}
.legend{{display:flex;flex-wrap:wrap;gap:8px 20px;font-size:13px;color:var(--muted)}} .legend i{{display:inline-block;width:14px;height:10px;margin-right:6px;vertical-align:-1px;border-radius:2px}}
svg.hist{{width:100%;height:auto;display:block}} .bar{{fill:var(--muted);opacity:.55}} .bar.hi{{fill:var(--over);opacity:1}} .bar.lo{{fill:var(--frame);opacity:1}}
.axis{{stroke:var(--rule)}} .tick{{font:400 13px var(--mono);fill:var(--muted);text-anchor:middle}}
.tbl{{overflow-x:auto}} table{{border-collapse:collapse;font:400 14px var(--mono);font-variant-numeric:tabular-nums;width:100%;min-width:420px}}
th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid var(--rule)}} th{{font:500 12px var(--body);color:var(--muted);letter-spacing:.04em;text-transform:uppercase}}
.note{{border-top:1px solid var(--rule);padding-top:20px;font-size:14px;color:var(--muted)}}
</style>
{P["defs"]}
<main>
<header style="display:grid;gap:14px">
<div class="eyebrow">Quran-Nazm · inspiration</div>
<h1>Beautiful hand, uneven pages</h1>
<p>Every line of the Madina Mushaf is the same width. The amount of text on those lines is not. This page measures all {s["n"]:,} full-width lines of the 1441H print, the current King Fahd Complex edition,, using its real line breaks set in a uniform digital reproduction of Uthman Taha's hand.</p>
</header>
<div class="stats">
<div class="stat"><b>{s["wmin"]}–{s["wmax"]}</b><span>words on a full line</span></div>
<div class="stat"><b>{s["lmin"]}–{s["lmax"]}</b><span>letters on a full line</span></div>
<div class="stat"><b>{s["rmin"]}–{s["rmax"]}%</b><span>natural length vs. line width</span></div>
<div class="stat"><b>{s["over"]+s["under"]}%</b><span>of lines off by more than 10%</span></div>
</div>
<section>
<div class="eyebrow">Page 156 · Al-Aʿrāf 44–51 · 1441H</div>
<h2>Fifteen lines, set at their natural length</h2>
<p>Each line below is shaped once, at one size, with no stretching. Dashed rules mark the print's line width. Red text runs past it and had to be squeezed in the print; green-tinted gaps had to be filled by stretching.</p>
<div class="legend"><span><i style="background:var(--overbg)"></i>too long, compressed in print</span><span><i style="background:var(--slack)"></i>too short, stretched in print</span></div>
<div class="spec">{P["A156"]}</div>
<p class="cap">Line 11 carries 10 words and runs 25% long. Line 2 carries 11 words yet runs only 2% short, and line 15 falls 15% short. Most of the page is overfull, so the print had to compress nearly every line except the last.</p>
</section>
<section>
<h2>How the print resolved page 156</h2>
<p>The same page in the 1441H print. Compare line 11, the longest at natural size, with line 15, the shortest: the first is visibly packed and the last is spaced out.</p>
<figure class="crop" style="max-width:520px"><img src="'+SCAN156+'" alt="Madina Mushaf 1441H, page 156"><figcaption><span>King Fahd Complex print · page 156</span><b>1441H</b></figcaption></figure>
</section>
<section>
<h2>What fitting by scaling does to the same page</h2>
<p>If each line is instead scaled as a whole to reach the line width, the size of the letters changes from line to line, and the pen stroke changes with it. This is a simulation of the mechanism, not a scan of the print.</p>
<div class="spec">{P["B156"]}</div>
<p class="cap">Scale factors on this page range from ×0.80 to ×1.18, so the largest line is drawn 48% bigger than the smallest.</p>
</section>
<section>
<div class="eyebrow">Page 72 · lines 10–12 · 1441H</div>
<h2>The sharpest jump between neighbours</h2>
<div class="spec">{P["A199"]}</div>
<p class="cap">All three lines hold 9 words. Line 10 runs 11% long, line 11 falls 22% short, and line 12 runs 14% long again. Word count alone does not predict the problem; the length of the words does.</p>
</section>
<section>
<h2>Across the whole Mushaf</h2>
<p>Natural length of every full line relative to the fixed width. A perfectly balanced setting would put every bar at 100%.</p>
<div class="spec" style="padding:16px">{P["H1"]}</div>
<p class="cap">{s["under"]}% of lines are more than 10% short (green) and {s["over"]}% are more than 10% long (red). The middle 90% of lines span {s["p5"]}% to {s["p95"]}%.</p>
<div class="spec" style="padding:16px">{P["H2"]}</div>
</section>
<section>
<h2>Where to look in your own copy</h2>
<p>The ten largest jumps between adjacent full lines in the 1441H print. Each can be checked directly in the King Fahd Complex PDF.</p>
<div class="tbl"><table><thead><tr><th>Page</th><th>Lines</th><th>Words</th><th>Natural length</th></tr></thead><tbody>{P["rows"]}</tbody></table></div>
</section>
<p class="note">Method: line breaks and text come from the DigitalKhatt layout of the 1441H Madina print, as used in quran-madina-html v2. Each line is shaped with HarfBuzz in the QMH New Madina font with no justification features, then compared with the print's line width. Lengths are relative to this font, so they show how much each real line had to be stretched or compressed, not exact millimetres on paper. Stroke weight cannot be measured from text data; it needs scans.</p>
</main>'''
open(WORK+'/quran-nazm-evidence.html','w').write(html);print(len(html)//1024,'KB')
