"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import sys,json,numpy as np
exec(open(HERE+'/62_render_single_line.py').read().split("HZ_=14")[0])
rows=[]
lines=[(w,t) for pg in ALL for p in pg for w,t in zip(*p)]
samp=[(w,t) for i,(w,t) in enumerate(lines) if i%3==0]
for sh in (0.10,0.15,0.20,0.25,0.35,0.45):
    W=ml*(1-sh);s=np.array([W/w for w,_ in lines])
    xs=np.array([J.justify_line(font,t,W).x_scale for w,t in samp if w>W]) if True else None
    nsamp=len(samp);sq_any=(xs<0.999).sum()/nsamp;sq5=(xs<0.95).sum()/nsamp
    r=dict(sh=sh,type=LW/W,med=float(np.median(s)),p5=float(np.percentile(s,5)),p95=float(np.percentile(s,95)),mn=float(s.min()),mx=float(s.max()),
        shr=float((s<1).mean()),shr10=float((s<0.9).mean()),sq_any=float(sq_any),sq5=float(sq5),xsmin=float(xs.min()) if len(xs) else 1.0,
        band=float(((s>=0.95)&(s<=1.19)).mean()))
    rows.append(r)
    print(f"≤{int(sh*100)}%: type {r['type']*100:.0f}% | median {r['med']:.2f} | 5-95% {r['p5']:.2f}-{r['p95']:.2f} | min {r['mn']:.2f} max {r['mx']:.2f} | 0.95-1.19 {r['band']*100:.0f}% | shrink {r['shr']*100:.0f}% (>10% {r['shr10']*100:.0f}%) | squeezed {r['sq_any']*100:.0f}% of all lines, >5% {r['sq5']*100:.1f}% | worst squeeze {(1-r['xsmin'])*100:.0f}%")
json.dump(rows,open(WORK+'/sweep2.json','w'))
