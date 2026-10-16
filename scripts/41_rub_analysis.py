"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import json,numpy as np
R=json.load(open(WORK+'/rub_minmax.json'));d=json.load(open(QMH+'/assets/db/v2/Madina-1441H.json'))
SP=100
# Madina 1441H lines used per rub'
ayas=[]
for si,su in enumerate(d['suras'],1):
    for ai,a in enumerate(su['ayas'][2:],1): ayas.append((si,ai,[(a['p'],x['l']) for x in a['r']]))
hdr={}
for si,su in enumerate(d['suras'],1): hdr[si]=[(a['p'],x['l']) for a in su['ayas'][:2] for x in a['r']]
for o in R:
    pl=set()
    for g in range(o['a0'],o['a1']):
        si,ai,rows=ayas[g-1];pl|=set(rows)
        if ai==1: pl|=set(hdr[si])
    o['madina_lines']=len(pl);o['madina_pages']=len(pl)/15
mp=np.array([o['madina_pages'] for o in R])
print('Madina pages per rub: min %.2f p5 %.2f median %.2f p95 %.2f max %.2f'%(mp.min(),*np.percentile(mp,[5,50,95]),mp.max()))
T=np.array([o['T'] for o in R]);WA=max(o['WA'] for o in R)
stretch=30*WA/T  # lower bound avg stretch per rub' (variant A)
print('variant A W* %.0f; avg stretch per rub: min %.2f p5 %.2f median %.2f p95 %.2f max %.2f'%(WA,stretch.min(),*np.percentile(stretch,[5,50,95]),stretch.max()))
for lim in (1.19,1.30,1.61,1.76): print(' rubs within',lim,'x:',int((stretch<=lim).sum()))
# grouping levels
def level(n):
    G=[T[i:i+n].sum() for i in range(0,240,n)];G=np.array(G);return G.max()/G.min(),G.std()/G.mean()
for n,name in [(1,'rub'),(2,'half hizb'),(4,'hizb'),(8,'juz')]: r,cv=level(n);print(f'{name}: longest/shortest {r:.2f}  cv {cv:.3f}')
top=sorted(R,key=lambda o:-o['T'])[:3];bot=sorted(R,key=lambda o:o['T'])[:3]
def loc(o):
    s,a=ayas[o['a0']-1][:2];s2,a2=ayas[o['a1']-2][:2];return f"{s}:{a}–{s2}:{a2}"
for o in top+bot: print(o['k'],loc(o),'T/LW %.1f'%(o['T']/15437.6),'Madina pages %.2f'%o['madina_pages'],'words',o['words'],'stretch %.2f'%(30*WA/o['T']))
json.dump(dict(R=R,WA=WA),open(WORK+'/rub_an.json','w'))
# sensitivity: W from percentile of required W (if top rubs handled differently)
Ws=np.sort([o['WA'] for o in R])
for k in (0,1,3,6,12):
    w=Ws[-1-k];s=30*w/T;s=s[[o['WA']<=w for o in R]]
    print(f'drop {k} longest: W {w/15437.6:.2f}x Madina, median stretch {np.median(s):.2f}, max {s.max():.2f}')
