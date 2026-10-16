"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import sys,json,statistics as st
sys.path.insert(0,QMH+'/src/db/v2'); sys.path.insert(0,'.')
import uharfbuzz as hb
from render_svg import GlyphPaths
m=json.load(open(WORK+'/m_1441H.json'))
full=[o for o in m if o['full']]
paths=GlyphPaths('madina.otf')
face=hb.Face(open(WORK+'/madina.otf','rb').read());font=hb.Font(face)
LW=15437.6; used=set()
def shape(t):
    b=hb.Buffer();b.add_str(t);b.guess_segment_properties();hb.shape(font,b,{})
    out,x=[],0
    for i,p in zip(b.glyph_infos,b.glyph_positions):
        out.append((i.codepoint,x+p.x_offset,p.y_offset));x+=p.x_advance
    return out,x
def uses(gl,dx,dy,s=1.0):
    r=[f'<g transform="translate({dx:.0f} {dy:.0f}) scale({s:.4f})">']
    for g,x,y in gl:
        if paths.path(g): used.add(g);r.append(f'<use href="#g{g}" x="{x:.0f}" y="{-y:.0f}"/>')
    return ''.join(r)+'</g>'
def page_svgs(p,lines_sel=None):
    ls=[o for o in m if o['p']==p and (lines_sel is None or o['l'] in lines_sel)]
    RH=2300; L,R=-4600,LW+3300
    A=[];B=[]
    for i,o in enumerate(ls):
        gl,w=shape(o['text']); y=i*RH+1500; r=w/LW
        x0=LW-w
        if w>LW: A.append(f'<rect class="over" x="{x0:.0f}" y="{y-1250}" width="{w-LW:.0f}" height="{RH-300}"/>')
        else: A.append(f'<rect class="slack" x="0" y="{y-1250}" width="{LW-w:.0f}" height="{RH-300}"/>')
        A.append(uses(gl,x0,y))
        A.append(f'<text class="lab {"hi" if r>1.1 else "lo" if r<0.9 else ""}" x="{LW+350}" y="{y-250}">{"+" if r>=1 else "−"}{abs(r-1)*100:.0f}%</text>')
        A.append(f'<text class="lab2" x="{LW+350}" y="{y+500}">{o["words"]} words</text>')
        s=LW/w
        B.append(uses(gl,0,y,s) if False else f'<g transform="translate(0 {y})">{uses(gl,0,0,s)}</g>')
        B.append(f'<text class="lab {"hi" if s<0.9 else "lo" if s>1.1 else ""}" x="{LW+350}" y="{y-250}">×{s:.2f}</text>')
    H=len(ls)*RH+400
    frame=f'<line class="edge" x1="0" y1="0" x2="0" y2="{H}"/><line class="edge" x1="{LW}" y1="0" x2="{LW}" y2="{H}"/>'
    def wrap(body,cls): return f'<svg class="{cls}" viewBox="{L} 0 {R-L} {H}" role="img">{frame}<g class="ink">{"".join(body)}</g></svg>'
    return wrap(A,'pg'),wrap(B,'pg'),ls
A156,B156,ls156=page_svgs(156)
A199,B199,ls72=page_svgs(72,{10,11,12})
# histograms
def hist(vals,lo,hi,n,fmt,xlabel,mark=None):
    bins=[0]*n;bw=(hi-lo)/n
    for v in vals:
        k=min(n-1,max(0,int((v-lo)/bw)));bins[k]+=1
    W,H,P=600,220,34;mx=max(bins);bwpx=(W-2*P)/n
    r=[f'<svg class="hist" viewBox="0 0 {W} {H+40}" role="img">']
    for i,c in enumerate(bins):
        h=(H-30)*c/mx;x=P+i*bwpx;v=lo+(i+.5)*bw
        cls='bar' if mark is None else ('bar hi' if v>mark[1] else 'bar lo' if v<mark[0] else 'bar')
        r.append(f'<rect class="{cls}" x="{x+1:.1f}" y="{H-h:.1f}" width="{bwpx-2:.1f}" height="{h:.1f}"/>')
    r.append(f'<line class="axis" x1="{P}" y1="{H}" x2="{W-P}" y2="{H}"/>')
    for t in fmt:
        x=P+(t-lo)/(hi-lo)*(W-2*P); r.append(f'<text class="tick" x="{x:.0f}" y="{H+20}">{fmt[t]}</text>')
    r.append(f'<text class="tick" x="{W/2}" y="{H+38}">{xlabel}</text></svg>')
    return ''.join(r)
rat=[o['ratio'] for o in full]
H1=hist(rat,0.5,1.4,36,{0.6:'60%',0.8:'80%',1.0:'100%',1.2:'120%',1.4:'140%'},'natural length of each line ÷ the fixed line width',(0.9,1.1))
wc=[o['words'] for o in full]
H2=hist(wc,3.5,15.5,12,{4:'4',6:'6',8:'8',10:'10',12:'12',14:'14'},'words per full-width line')
over=sum(r>1.1 for r in rat)/len(rat)*100; under=sum(r<0.9 for r in rat)/len(rat)*100
lc=[o['letters'] for o in full]
stats=dict(n=len(full),over=round(over),under=round(under),wmin=min(wc),wmax=max(wc),lmin=min(lc),lmax=max(lc),rmin=round(min(rat)*100),rmax=round(max(rat)*100),p5=round(sorted(rat)[len(rat)//20]*100),p95=round(sorted(rat)[-len(rat)//20]*100))
# neighbour table
by={}
for o in full: by.setdefault(o['p'],{})[o['l']]=o
pairs=[]
for p,d in by.items():
    for l,a in d.items():
        b=d.get(l+1)
        if b: pairs.append((abs(a['ratio']-b['ratio']),a,b))
pairs.sort(key=lambda t:-t[0])
rows=''.join(f'<tr><td>{a["p"]}</td><td>{a["l"]}–{b["l"]}</td><td>{a["words"]} → {b["words"]}</td><td>{a["ratio"]*100:.0f}% → {b["ratio"]*100:.0f}%</td></tr>' for _,a,b in pairs[:10])
defs='<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>'+''.join(f'<path id="g{g}" d="{paths.path(g)}"/>' for g in sorted(used))+'</defs></svg>'
P156=[dict(l=o['l'],r=o['ratio'],w=o['words']) for o in ls156];P72=[dict(l=o['l'],r=o['ratio'],w=o['words']) for o in ls72]
json.dump(dict(P156=P156,P72=P72,A156=A156,B156=B156,A199=A199,B199=B199,H1=H1,H2=H2,stats=stats,rows=rows,defs=defs),open(WORK+'/parts.json','w'),ensure_ascii=False)
print(stats,len(defs)//1024,'KB defs',len(A156)//1024)
