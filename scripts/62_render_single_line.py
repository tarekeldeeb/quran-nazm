"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import sys,json,numpy as np
sys.path.insert(0,QMH+'/src/db/v2')
import uharfbuzz as hb, justify as J
from render_svg import GlyphPaths
src=open(HERE+'/61_single_line_refined.py').read()
src=src.replace("    b=b[::-1];return [cum[e]-cum[s]-SP for s,e in zip(b[:-1],b[1:])]","    b=b[::-1];return b")
src=src.replace("        out.append(opt_lines(ws,L))","        b=opt_lines(ws,L);U=units[s:e];cu=np.concatenate([[0],np.cumsum(np.array(ws)+SP)]);out.append(([cu[y]-cu[x]-SP for x,y in zip(b[:-1],b[1:])],[' '.join(u[0] for u in U[x:y]) for x,y in zip(b[:-1],b[1:])]))")
src=src.split('def run(joint)')[0]
exec(src)
font=hb.Font(hb.Face(open(WORK+'/madina.otf','rb').read()));paths=GlyphPaths(WORK+'/madina.otf')
ALL=[pages_of(A,True) for A in H];ml=max(max(p[0]) for pg in ALL for p in pg)
HZ_=14;pg=ALL[HZ_-1][0];used=set();out={}
for sh in (0.10,0.15,0.20,0.25):
    W=ml*(1-sh);pitch=0.1086*W;g_all=[];st=[]
    for i,t in enumerate(pg[1]):
        r=J.justify_line(font,t,W);gl,x=J.line_glyphs(font,t,r);xs=r.x_scale;st.append(W/r.natural_width)
        y=i*pitch+0.68*pitch;x0=W-x*xs;g=[f'<g transform="translate({x0:.0f} {y:.0f}) scale({xs:.4f} 1)">']
        for gid,gx,gy in gl:
            if paths.path(gid): used.add(gid);g.append(f'<use href="#g{gid}" x="{gx:.0f}" y="{-gy:.0f}"/>')
        g_all.append(''.join(g)+'</g>')
    m=0.04*W;st=np.array(st)
    allst=np.array([W/w for P_ in ALL for p in P_ for w in p[0]])
    svg=f'<svg class="pg" viewBox="{-m:.0f} {-m:.0f} {W+2*m:.0f} {15*pitch+2*m:.0f}" role="img"><rect class="frame" x="{-m*0.5:.0f}" y="{-m*0.5:.0f}" width="{W+m:.0f}" height="{15*pitch+m:.0f}" rx="{m*0.3:.0f}"/><g class="ink">{"".join(g_all)}</g></svg>'
    out[int(round(sh*100))]=dict(svg=svg,type=LW/W,med=float(np.median(st)),mn=float(st.min()),mx=float(st.max()),gmed=float(np.median(allst)),gp95=float(np.percentile(allst,95)),gmax=float(allst.max()),gshr=float((allst<1).mean()))
    print(sh,f"type {LW/W:.2f} page {np.median(st):.2f} [{st.min():.2f},{st.max():.2f}] ends ...{pg[1][-1][-15:]} nlines {len(pg[1])}")
defs='<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>'+''.join(f'<path id="g{g}" d="{paths.path(g)}"/>' for g in sorted(used))+'</defs></svg>'
json.dump(dict(pages=out,defs=defs),open(WORK+'/render_t.json','w'),ensure_ascii=False)
