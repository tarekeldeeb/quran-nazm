"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import json,numpy as np
U=json.load(open(WORK+'/rub_units.json'));R=json.load(open(WORK+'/rub_minmax.json'));SP=100;LW=15437.6
def lines_needed(ws,Wm):
    n=1;cur=-SP
    for w in ws:
        if cur+SP+w<=Wm: cur+=SP+w
        else: n+=1;cur=w
    return n
def minmax(ws,L):
    lo=max(ws);hi=sum(ws)+SP*len(ws)
    for _ in range(45):
        mid=(lo+hi)/2
        if lines_needed(ws,mid)<=L: hi=mid
        else: lo=mid
    return hi
def even_break(ws,L,Wm):
    # place breaks near k*T/L, never exceeding Wm (fallback to greedy repair)
    n=len(ws);cum=np.cumsum(np.array(ws)+SP);T=cum[-1];lines=[];start=0
    for k in range(1,L):
        target=k*T/L
        best=None
        for e in range(start+1,n-(L-k)+1):
            w=cum[e-1]-(cum[start-1] if start else 0)-SP
            if w>Wm: break
            if best is None or abs(cum[e-1]-target)<abs(cum[best-1]-target): best=e
        if best is None: best=start+1
        lines.append(cum[best-1]-(cum[start-1] if start else 0)-SP);start=best
    lines.append(cum[-1]-(cum[start-1] if start else 0)-SP)
    return np.array(lines)
def hdr(heads,mode):
    if mode=='A': return 0
    return sum((1 if s in (1,9) else 2) if mode=='B' else 1 for s in heads)
res={}
for pages in (8,10):
    for mode in 'ABC':
        G=[];H=[]
        for h in range(60):
            ws=[w for r in range(4*h,4*h+4) for _,w in U[r]];heads=[s for r in range(4*h,4*h+4) for s in R[r]['heads']]
            G.append(ws);H.append(hdr(heads,mode))
        L=[pages*15-x for x in H]
        Wr=np.array([minmax(g,l) for g,l in zip(G,L)]);Wm=Wr.max()
        st=[];pagestd=[];hz=[]
        for g,l in zip(G,L):
            lw=even_break(g,l,Wm);s=Wm/lw;st+=list(s);hz.append(np.mean(s))
            for p in range(0,len(s),15): pagestd.append(np.std(s[p:p+15]))
        st=np.array(st);hz=np.array(hz)
        res[(pages,mode)]=dict(W=Wm/LW,worst=int(np.argmax(Wr))+1,minL=min(L),med=np.median(st),p95=np.percentile(st,95),mx=st.max(),
            in119=(st<=1.19).mean(),in130=(st<=1.30).mean(),over176=(st>1.76).mean(),hzmin=hz.min(),hzmax=hz.max(),pstd=np.median(pagestd),
            total=pages*60,sparse=int(np.argmax([0]+[0]) ))
        r=res[(pages,mode)]
        print(f"{pages}p {mode}: line {r['W']:.2f}x Madina (type {1/r['W']*100:.0f}% size), set by hizb {r['worst']}, fewest text lines {r['minL']} | per-line stretch median {r['med']:.2f} p95 {r['p95']:.2f} max {r['mx']:.2f} | <=1.19x {r['in119']*100:.0f}%  <=1.30x {r['in130']*100:.0f}%  >1.76x {r['over176']*100:.1f}% | hizb avg stretch {r['hzmin']:.2f}-{r['hzmax']:.2f} | page stretch sd {r['pstd']:.3f}")
print('--- headers Madina-style (B), width set without hizb 60, which gets 1-line headers (C)')
for pages in (8,10):
    G=[];L=[]
    for h in range(60):
        ws=[w for r in range(4*h,4*h+4) for _,w in U[r]];heads=[s for r in range(4*h,4*h+4) for s in R[r]['heads']]
        G.append(ws);L.append(pages*15-hdr(heads,'C' if h==59 else 'B'))
    Wr=np.array([minmax(g,l) for g,l in zip(G,L)]);order=np.argsort(-Wr);Wm=Wr.max()
    st=[];pg=[]
    for g,l in zip(G,L):
        s=Wm/even_break(g,l,Wm);st+=list(s)
        for p in range(0,len(s),15): pg.append(np.std(s[p:p+15]))
    st=np.array(st)
    print(f"{pages}p: line {Wm/LW:.2f}x Madina (type {LW/Wm*100:.0f}%), set by hizb {order[0]+1} then {order[1]+1},{order[2]+1} | stretch median {np.median(st):.2f} p95 {np.percentile(st,95):.2f} max {st.max():.2f} | <=1.19 {(st<=1.19).mean()*100:.0f}% <=1.30 {(st<=1.3).mean()*100:.0f}% >1.76 {(st>1.76).mean()*100:.1f}% | page sd {np.median(pg):.3f} | hizb60 text lines {L[59]}")
heads=[(h+1,sum(len(R[r]['heads']) for r in range(4*h,4*h+4))) for h in range(60)];print('suras starting per hizb (top)',sorted(heads,key=lambda x:-x[1])[:5])
print('--- hizbs 1-59 with Madina-style headers; hizb 60 handled separately')
for pages in (8,10):
    G=[];L=[]
    for h in range(60):
        ws=[w for r in range(4*h,4*h+4) for _,w in U[r]];heads=[s for r in range(4*h,4*h+4) for s in R[r]['heads']]
        G.append((ws,heads));L.append(pages*15-hdr(heads,'B'))
    Wr=np.array([minmax(g,l) for (g,_),l in zip(G[:59],L[:59])]);Wm=Wr.max();order=np.argsort(-Wr)
    st=[];pg=[];hz=[]
    for (g,_),l in zip(G[:59],L[:59]):
        s=Wm/even_break(g,l,Wm);st+=list(s);hz.append(s.mean())
        for p in range(0,len(s),15): pg.append(np.std(s[p:p+15]))
    st=np.array(st);hz=np.array(hz)
    g60,h60=G[59];need=lines_needed(g60,Wm)+hdr(h60,'B')
    print(f"{pages}p: line {Wm/LW:.2f}x Madina (type {LW/Wm*100:.0f}%), set by hizb {order[0]+1},{order[1]+1},{order[2]+1} | stretch median {np.median(st):.2f} p95 {np.percentile(st,95):.2f} max {st.max():.2f} | <=1.19 {(st<=1.19).mean()*100:.0f}% <=1.30 {(st<=1.3).mean()*100:.0f}% >1.50 {(st>1.5).mean()*100:.0f}% >1.76 {(st>1.76).mean()*100:.1f}% | sparsest hizb avg {hz.max():.2f} (hizb {np.argmax(hz)+1}) | page sd {np.median(pg):.3f} | hizb60 needs {need} lines = {need/15:.1f} pages")
print('--- hizbs 1-58 only (juz 30 excluded), Madina-style headers')
for pages in (8,10):
    G=[];L=[]
    for h in range(58):
        ws=[w for r in range(4*h,4*h+4) for _,w in U[r]];heads=[s for r in range(4*h,4*h+4) for s in R[r]['heads']]
        G.append(ws);L.append(pages*15-hdr(heads,'B'))
    Wr=np.array([minmax(g,l) for g,l in zip(G,L)]);Wm=Wr.max();order=np.argsort(-Wr)
    st=[];pg=[];hz=[];wpl=[]
    for g,l in zip(G,L):
        s=Wm/even_break(g,l,Wm);st+=list(s);hz.append(s.mean());wpl.append(len(g)/l)
        for p in range(0,len(s),15): pg.append(np.std(s[p:p+15]))
    st=np.array(st);hz=np.array(hz)
    print(f"{pages}p: line {Wm/LW:.2f}x (type {LW/Wm*100:.0f}%), set by {order[0]+1},{order[1]+1},{order[2]+1} | med {np.median(st):.2f} p95 {np.percentile(st,95):.2f} max {st.max():.2f} | <=1.19 {(st<=1.19).mean()*100:.0f}% <=1.30 {(st<=1.3).mean()*100:.0f}% >1.50 {(st>1.5).mean()*100:.1f}% >1.76 {(st>1.76).mean()*100:.2f}% | hizb avg {hz.min():.2f}-{hz.max():.2f} (sparsest {np.argmax(hz)+1}) | page sd {np.median(pg):.3f} | words/line {np.mean(wpl):.1f} | pages {pages*58}")
