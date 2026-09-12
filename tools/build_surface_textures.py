"""Deterministic, tileable linear-data textures for the clockwork shaders.
No external images: walnut grain/pore/roughness and metal wear/scratches/grit.
Run python3 tools/build_surface_textures.py. RGB channels are data, not albedo.
"""
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image
OUT=Path(__file__).resolve().parents[1]/'harness/assets/textures'
OUT.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(73091)
n=1024
y,x=np.mgrid[:n,:n]/n

def noise(sigma):
    z=gaussian_filter(rng.normal(size=(n,n)),sigma,mode='wrap')
    return (z-z.mean())/(z.std()+1e-9)
def unit(a): return np.clip(.5+a*.16,0,1)
def save(name,*channels):
    Image.fromarray(np.uint8(np.stack(channels,axis=-1).clip(0,1)*255)).save(OUT/name)
# Fibres run along image X; a periodic warp avoids obvious straight pinstripes.
warp=.025*np.sin(2*np.pi*x)+.010*np.sin(6*np.pi*x+3*np.sin(2*np.pi*y))
long=noise((1.5,58)); broad=noise((22,110)); fine=noise((.45,20))
phase=(y+warp)*2*np.pi
rings=np.sin(phase*32+1.1*broad)+.35*np.sin(phase*73+.5*long)
grain=unit(.55*rings+.75*long+.3*broad)
pores=np.clip((fine+long*.3-1.15)*.65,0,1)
rough=unit(.5*noise(1.2)+.4*long)
save('walnut_data.png',grain,pores,rough)
patch=noise(34)*.6+noise(8)*.25
scratch=noise((.5,50))*.65+noise((.6,7))*.25
micro=noise(.55)
save('metal_data.png',unit(patch),unit(scratch),unit(micro))
save('felt_data.png',unit(noise(.5)),unit(noise((.5,2))),unit(noise((2,.5))))
print('Wrote 3 tileable 1024px packed surface maps to',OUT)
