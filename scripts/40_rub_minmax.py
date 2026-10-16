"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import sys,json,re,numpy as np
sys.path.insert(0,QMH+'/src/db/v2')
import uharfbuzz as hb, justify as J
font=hb.Font(hb.Face(open(WORK+'/madina.otf','rb').read()))
SP=J.width(font,' ');AYA=J.AYA_SPACE
d=json.load(open(QMH+'/assets/db/v2/Madina-1441H.json'));Q=json.load(open(DATA+'/hafs-rub-start-ayahs.json'))
starts=Q[1:241]
# units per global aya index
ayas=[];sura_of=[]
for si,su in enumerate(d['suras'],1):
    for ai,a in enumerate(su['ayas'][2:],1):
        t=' '.join(r['t'].strip() for r in a['r'] if r['t'].strip())
        ayas.append((si,ai,t))
assert len(ayas)==6236,len(ayas)
wcache={}
def W(t):
    if t not in wcache: wcache[t]=J.width(font,t)
    return wcache[t]
def units_of(text):
    toks=text.split();U=[]
    for tk in toks:
        if tk.startswith('۝') and U: U[-1]=(U[-1][0]+' '+tk, U[-1][1]+SP*AYA+W(tk))
        else: U.append((tk,W(tk)))
    return U
rubs=[]
for k in range(240):
    a0,a1=starts[k],(starts[k+1] if k<239 else 6237)
    U=[];heads=[]
    for g in range(a0,a1):
        si,ai,t=ayas[g-1]
        if ai==1: heads.append(si)
        U+=units_of(t)
    rubs.append(dict(k=k+1,a0=a0,a1=a1,units=U,heads=heads))
def lines_needed(ws,Wmax):
    n=1;cur=-SP
    for w in ws:
        if w>Wmax: return 10**9
        if cur+SP+w<=Wmax: cur+=SP+w
        else: n+=1;cur=w
    return n
def minmax(ws,L):
    lo=max(ws);hi=sum(ws)+SP*len(ws)
    if L<=0: return float('inf')
    for _ in range(40):
        mid=(lo+hi)/2
        if lines_needed(ws,mid)<=L: hi=mid
        else: lo=mid
    return hi
def header_lines(heads,mode):
    if mode=='A': return 0
    c=0
    for s in heads:
        if mode=='B': c+= 1 if s in (1,9) else 2
        else: c+=1
    return c
out=[]
for r in rubs:
    ws=[u[1] for u in r['units']];T=sum(ws)+SP*(len(ws)-1)
    row=dict(k=r['k'],a0=r['a0'],a1=r['a1'],words=len(ws),T=T,heads=r['heads'])
    for mode in 'ABC':
        L=30-header_lines(r['heads'],mode);row['L'+mode]=L
        row['W'+mode]=minmax(ws,L) if L>0 else None
    out.append(row)
json.dump(out,open(WORK+'/rub_minmax.json','w'))
json.dump([[u for u in r['units']] for r in rubs],open(WORK+'/rub_units.json','w'),ensure_ascii=False)
LW=d['line_width']*1000
print('Madina line width',LW,'space',SP)
for mode in 'ABC':
    ok=[o for o in out if o['W'+mode]];bad=[o['k'] for o in out if not o['W'+mode]]
    Ws=np.array([o['W'+mode] for o in ok]);fill=np.array([o['T']/(o['L'+mode]*Ws.max()) for o in ok])
    i=int(np.argmax(Ws))
    print(mode,'rubs',len(ok),'no-room',bad[:10],len(bad),'W* =',round(Ws.max()),f'({Ws.max()/LW:.2f}x Madina) at rub',ok[i]['k'],'min W',round(Ws.min()),'avg fill min/med',fill.min().round(3),np.median(fill).round(3))
T=np.array([o['T'] for o in out]);print('rub text length / Madina line: min',(T.min()/LW).round(1),'max',(T.max()/LW).round(1),'ratio',(T.max()/T.min()).round(2))
print('heads per rub top',sorted(((len(o['heads']),o['k']) for o in out),reverse=True)[:6])
