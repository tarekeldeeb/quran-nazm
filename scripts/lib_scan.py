"""Quran-Nazm research script. Paths come from paths.py (QMH, SCAN_PDF, NAZM_WORK)."""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import *
import numpy as np,cv2
def load(i):
    im=cv2.imread(f'{SCAN}/{i:03d}.png')
    hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV);g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
    colored=(hsv[...,1]>60)&(hsv[...,2]>60)
    return im,g,colored
def frame(colored):
    # inner frame: longest colored rows/cols
    H,W=colored.shape
    rows=colored.sum(1);cols=colored.sum(0)
    rr=np.where(rows>0.6*W)[0];cc=np.where(cols>0.6*H)[0]
    return rr,cc
