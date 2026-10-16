"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import sys,json
sys.path.insert(0,QMH+'/src/db/v2')
import uharfbuzz as hb, justify as J
font=hb.Font(hb.Face(open(WORK+'/madina.otf','rb').read()));SP=J.width(font,' ');AYA=J.AYA_SPACE
d=json.load(open(QMH+'/assets/db/v2/Madina-1441H.json'));Q=json.load(open(DATA+'/hafs-rub-start-ayahs.json'))
ayas=[]
for si,su in enumerate(d['suras'],1):
    for ai,a in enumerate(su['ayas'][2:],1):
        ayas.append((si,ai,' '.join(r['t'].strip() for r in a['r'] if r['t'].strip())))
wc={}
def W(t):
    if t not in wc: wc[t]=J.width(font,t)
    return wc[t]
H=[]
for h in range(60):
    a0=Q[1+4*h];a1=Q[1+4*h+4] if 4*h+4<240 else 6237
    A=[]
    for g in range(a0,a1):
        si,ai,t=ayas[g-1];U=[]
        for tk in t.split():
            if tk.startswith('۝') and U: U[-1]=[U[-1][0]+' '+tk,U[-1][1]+SP*AYA+W(tk)]
            else: U.append([tk,W(tk)])
        hdr=0 if ai!=1 else (1 if si in (1,9) else 2)
        A.append(dict(s=si,a=ai,u=U,hdr=hdr))
    H.append(A)
json.dump(H,open(WORK+'/hizb_ayas.json','w'),ensure_ascii=False)
longest=max((sum(w for _,w in A['u'])+SP*len(A['u']),A['s'],A['a']) for h in H for A in h)
print('done; longest ayah natural width / Madina line:',round(longest[0]/15437.6,1),longest[1:])
