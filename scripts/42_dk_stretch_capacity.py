"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import sys,json,random,numpy as np
sys.path.insert(0,QMH+'/src/db/v2')
import uharfbuzz as hb, justify as J
from concurrent.futures import ProcessPoolExecutor
def cap(text):
    font=hb.Font(hb.Face(open(WORK+'/madina.otf','rb').read()))
    line=J.analyze_line(text);sw=J.width(font,' ')
    n_aya=sum(1 for t in line.spaces.values() if t=='aya');n_s=len(line.spaces)-n_aya
    nat=sum(J.width(font,w.text) for w in line.words)+sw*n_s+sw*J.AYA_SPACE*n_aya
    spaces=min(100,sw)*1.0*n_s+min(200,2*sw)*1.0*n_aya
    cur=nat+spaces
    j=J._Justifier(font,line,cur,nat*4,True);j.run()
    return nat,j.text_width,cur
if __name__=='__main__':
    m=[o for o in json.load(open(WORK+'/m_1441H.json')) if o['full']]
    random.seed(1);S=random.sample(m,400)
    with ProcessPoolExecutor() as ex: R=list(ex.map(cap,[o['text'] for o in S]))
    r=np.array([b/a for a,b,c in R]);sp=np.array([c/a for a,b,c in R])
    print('capacity (letters+spaces) pct',np.percentile(r,[5,25,50,75,95]).round(3),'spaces only',np.percentile(sp,[5,50,95]).round(3))
    json.dump(R,open(WORK+'/cap_sample.json','w'))
