"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import sys,json,re,statistics as st
sys.path.insert(0,'.')
from lib_load import load
import uharfbuzz as hb
AYA=re.compile(r'۝')
def run(lay,fontfile):
    d,txt=load(lay)
    face=hb.Face(open(fontfile,'rb').read());font=hb.Font(face);upem=face.upem
    LW=d['line_width']*1000 if d['line_width']<100 else d['line_width']
    out=[]
    for p,page in enumerate(d['lines'],1):
        for l,row in enumerate(page,1):
            if row['k']!='text': continue
            parts=txt.get((p,l))
            if not parts: continue
            s=' '.join(t for t,_ in parts)
            buf=hb.Buffer();buf.add_str(s);buf.guess_segment_properties()
            hb.shape(font,buf,{})
            w=sum(g.x_advance for g in buf.glyph_positions)/upem
            words=[w_ for w_ in s.split() if not w_.startswith('۝')]
            letters=len(re.sub(r'[^ء-يٱ-ۓ]','',s))
            full=abs(row['w']-d['line_width'])<1e-3
            out.append(dict(p=p,l=l,text=s,nat=w,target=row['w'],ratio=w/row['w'],words=len(words),letters=letters,full=full,x=row.get('x',1)))
    json.dump(out,open(f'm_{lay}.json','w'),ensure_ascii=False)
    full=[o for o in out if o['full']]
    r=[o['ratio'] for o in full];wc=[o['words'] for o in full];lc=[o['letters'] for o in full]
    print(lay,len(full),'ratio min/med/max',round(min(r),3),round(st.median(r),3),round(max(r),3),'sd',round(st.pstdev(r),3))
    print(' words min/med/max',min(wc),st.median(wc),max(wc),' letters',min(lc),st.median(lc),max(lc))
    q=sorted(r);print(' p5,p95',round(q[len(q)//20],3),round(q[-len(q)//20],3))
run('1405H','oldmadina.otf');run('1441H','madina.otf')
