"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import json,cv2,base64,numpy as np
W=json.load(open(WORK+'/w_1441H.json'));F=[o for o in W if o['full']]
w={(o['p'],o['l']):o for o in W}
for o in F: o['ipl']=o['ink']/o['letters']
# same-page ink-per-letter contrast
by={}
for o in F: by.setdefault(o['p'],[]).append(o)
best=max(by.values(),key=lambda v:max(x['ipl'] for x in v)/min(x['ipl'] for x in v))
hi=max(best,key=lambda x:x['ipl']);lo=min(best,key=lambda x:x['ipl'])
print('ipl page',hi['p'],hi['l'],round(hi['ipl']),hi['words'],round(hi['ratio'],2),'|',lo['l'],round(lo['ipl']),lo['words'],round(lo['ratio'],2))
def crop(k):
    o=w[k];x0,a,x1,b=o['box'];im=cv2.imread(f'{SCAN}/{k[0]:03d}.png')[a:b,x0:x1]
    im=cv2.resize(im,None,fx=1.5,fy=1.5,interpolation=cv2.INTER_CUBIC)
    ok,buf=cv2.imencode('.png',im);return 'data:image/png;base64,'+base64.b64encode(buf).decode()
crops={f'{p}_{l}':crop((p,l)) for p,l in [(102,4),(102,5),(561,9),(563,9),(hi['p'],hi['l']),(lo['p'],lo['l'])]}
sw=np.array([o['sw'] for o in F]);RA=np.array([o["ratio"] for o in F]);ipl=np.array([o['ipl'] for o in F])
bins=[(0.6,0.8,'under 80%'),(0.8,0.9,'80–90%'),(0.9,1.0,'90–100%'),(1.0,1.1,'100–110%'),(1.1,1.2,'110–120%'),(1.2,1.4,'over 120%')]
B=[]
for a,b,lab in bins:
    s=(RA>=a)&(RA<b);B.append(dict(lab=lab,n=int(s.sum()),sw=float(sw[s].mean()),ipl=float(ipl[s].mean())))
def bars(key,vmin,vmax,fmt,unit):
    Wd,H,P,L=600,250,40,48;bw=(Wd-L-P)/len(B);r=[f'<svg class="hist" viewBox="0 0 {Wd} {H+44}" role="img">']
    for t in np.linspace(vmin,vmax,4):
        y=H-(t-vmin)/(vmax-vmin)*(H-30);r.append(f'<line class="axis" x1="{L}" y1="{y:.0f}" x2="{Wd-P}" y2="{y:.0f}" opacity=".5"/><text class="tick" x="{L-8}" y="{y+4:.0f}" style="text-anchor:end">{fmt(t)}</text>')
    for i,b_ in enumerate(B):
        v=b_[key];h=(v-vmin)/(vmax-vmin)*(H-30);x=L+i*bw
        cls='bar lo' if i==0 else 'bar hi' if i==len(B)-1 else 'bar'
        r.append(f'<rect class="{cls}" x="{x+8:.0f}" y="{H-h:.0f}" width="{bw-16:.0f}" height="{h:.0f}"/><text class="tick" x="{x+bw/2:.0f}" y="{H-h-8:.0f}">{fmt(v)}</text><text class="tick" x="{x+bw/2:.0f}" y="{H+18}">{b_["lab"]}</text>')
    r.append(f'<text class="tick" x="{(L+Wd-P)/2:.0f}" y="{H+40}">natural length of the line (how crowded it is)</text></svg>');return ''.join(r)
C1=bars('sw',2.1,2.36,lambda v:f'{v:.2f}','px');C2=bars('ipl',90,135,lambda v:f'{v:.0f}','')
# page strip
pm={};[pm.setdefault(o['p'],[]).append(o['sw']) for o in W];pm={p:float(np.mean(v)) for p,v in pm.items()}
ps=sorted(pm);vals=np.array([pm[p] for p in ps]);lo_,hi_=1.95,2.75
Wd,H,L,P=600,200,40,16;r=[f'<svg class="hist" viewBox="0 0 {Wd} {H+44}" role="img">']
for t in [2.0,2.2,2.4,2.6]:
    y=H-(t-lo_)/(hi_-lo_)*(H-10);r.append(f'<line class="axis" x1="{L}" y1="{y:.0f}" x2="{Wd-P}" y2="{y:.0f}" opacity=".5"/><text class="tick" x="{L-6}" y="{y+4:.0f}" style="text-anchor:end">{t:.1f}</text>')
for p in ps:
    x=L+(p-3)/(604-3)*(Wd-L-P);y=H-(pm[p]-lo_)/(hi_-lo_)*(H-10)
    cls='dot hi' if p==561 else 'dot lo' if p==563 else 'dot'
    r.append(f'<circle class="{cls}" cx="{x:.1f}" cy="{y:.1f}" r="{4 if p in(561,563) else 1.8}"/>')
for p,lab in [(561,'561'),(563,'563')]:
    x=L+(p-3)/(604-3)*(Wd-L-P);y=H-(pm[p]-lo_)/(hi_-lo_)*(H-10);r.append(f'<text class="tick" x="{x-10:.0f}" y="{y+(-10 if p==561 else 18):.0f}" style="text-anchor:end">p. {lab}</text>')
for t in [100,200,300,400,500,600]:
    x=L+(t-3)/(604-3)*(Wd-L-P);r.append(f'<text class="tick" x="{x:.0f}" y="{H+20}">{t}</text>')
r.append(f'<text class="tick" x="{(L+Wd-P)/2:.0f}" y="{H+40}">page number · average pen width in px</text></svg>');C3=''.join(r)
pages=len({o['p'] for o in F})
J=[]
for p,v in by.items():
    d={x['l']:x for x in v}
    for l,x in d.items():
        y=d.get(l+1)
        if y: J.append(max(x['sw'],y['sw'])/min(x['sw'],y['sw']))
pr=[max(x['sw'] for x in v)/min(x['sw'] for x in v) for v in by.values()]
S=dict(n=len(F),pages=pages,p5=float(np.percentile(sw,5)),p95=float(np.percentile(sw,95)),pagemed=float(np.median(pr)),adjmax=float(max(J)),
 adj10=int(sum(j>=1.10 for j in J)),i5=float(np.percentile(ipl,5)),i95=float(np.percentile(ipl,95)),corr=float(np.corrcoef(ipl,RA)[0,1]),
 p561=pm[561],p563=pm[563],p559=pm[559],hi=dict(p=hi['p'],l=hi['l'],ipl=hi['ipl'],w=hi['words'],r=hi['ratio']),lo=dict(p=lo['p'],l=lo['l'],ipl=lo['ipl'],w=lo['words'],r=lo['ratio']),B=B,
 s102=[w[(102,4)]['sw'],w[(102,5)]['sw']],s561=w[(561,9)]['sw'],s563=w[(563,9)]['sw'])
json.dump(dict(S=S,crops=crops,C1=C1,C2=C2,C3=C3),open(WORK+'/ch2.json','w'))
print(json.dumps({k:v for k,v in S.items() if k!='B'},default=str)[:900]);print(B)
