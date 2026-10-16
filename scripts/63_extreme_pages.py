"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import sys,json,numpy as np
exec(open(HERE+'/62_render_single_line.py').read().split("HZ_=14")[0])
W=ml*0.75;pitch=0.1086*W;used=set()
hz=[np.mean([W/w for p in pg for w in p[0]]) for pg in ALL]
hd,hs=int(np.argmin(hz)),int(np.argmax(hz))
print('densest hizb',hd+1,round(hz[hd],3),'sparsest hizb',hs+1,round(hz[hs],3))
d=json.load(open(QMH+'/assets/db/v2/Madina-1441H.json'));Hq=json.load(open(WORK+'/hizb_ayas.json'))
def render(h,pi):
    pg=ALL[h][pi];g_all=[];st=[];xs_all=[]
    for i,t in enumerate(pg[1]):
        r=J.justify_line(font,t,W);gl,x=J.line_glyphs(font,t,r);xs=r.x_scale;st.append(W/r.natural_width);xs_all.append(xs)
        y=i*pitch+0.68*pitch;x0=W-x*xs;g=[f'<g transform="translate({x0:.0f} {y:.0f}) scale({xs:.4f} 1)">']
        for gid,gx,gy in gl:
            if paths.path(gid): used.add(gid);g.append(f'<use href="#g{gid}" x="{gx:.0f}" y="{-gy:.0f}"/>')
        g_all.append(''.join(g)+'</g>')
    L=len(pg[1]);top=(15-L)*pitch  # header lines sit at top as blank rows
    m=0.04*W
    svg=f'<svg class="pg" viewBox="{-m:.0f} {-m:.0f} {W+2*m:.0f} {15*pitch+2*m:.0f}" role="img"><rect class="frame" x="{-m*0.5:.0f}" y="{-m*0.5:.0f}" width="{W+m:.0f}" height="{15*pitch+m:.0f}" rx="{m*0.3:.0f}"/><g class="ink" transform="translate(0 {top:.0f})">{"".join(g_all)}</g></svg>'
    return svg,np.array(st),np.array(xs_all),L
res={}
for tag,h,fn in [('dense',hd,np.argmin),('sparse',hs,np.argmax)]:
    pm=[np.mean([W/w for w in p[0]]) for p in ALL[h]];pi=int(fn(pm))
    svg,st,xs,L=render(h,pi)
    # ayah range of the page
    first=ALL[h][pi][1][0][:40];last=ALL[h][pi][1][-1][-20:]
    res[tag]=dict(h=h+1,page=pi+1,svg=svg,mean=float(st.mean()),mn=float(st.min()),mx=float(st.max()),xs=float(xs.min()),nsq=int((xs<0.999).sum()),L=L,hz=float(hz[h]))
    print(tag,'hizb',h+1,'page',pi+1,'lines',L,f'mean {st.mean():.2f} [{st.min():.2f},{st.max():.2f}] min x-scale {xs.min():.3f} squeezed lines {(xs<0.999).sum()}', '| starts',first,'| ends',last)
# Mushaf-wide squeeze check at 25%
sq=[];
for pg in ALL[::2]:
    for p in pg:
        for w,t in zip(*p):
            if w>W: sq.append(J.justify_line(font,t,W).x_scale)
sq=np.array(sq);print('compressed lines checked',len(sq),'needing horizontal squeeze',f'{(sq<0.999).mean()*100:.0f}%','>3%',f'{(sq<0.97).mean()*100:.0f}%','>5%',f'{(sq<0.95).mean()*100:.1f}%','min',round(sq.min(),3))
res['sq']=dict(n=len(sq),any=float((sq<0.999).mean()),p3=float((sq<0.97).mean()),p5=float((sq<0.95).mean()),mn=float(sq.min()))
res['defs']='<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>'+''.join(f'<path id="h{g}" d="{paths.path(g)}"/>' for g in sorted(used))+'</defs></svg>'
for k in ('dense','sparse'): res[k]['svg']=res[k]['svg'].replace('href="#g','href="#h')
json.dump(res,open(WORK+'/extremes.json','w'),ensure_ascii=False)
