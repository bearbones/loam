"""Linear data maps for formed glass and the workshop's pitch stamps."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter

OUT = Path(__file__).resolve().parents[1]/'harness/assets/textures'


def furnace_glass():
    rng=np.random.default_rng(1874)
    n=768
    y,x=np.mgrid[:n,:n]/n
    warp=gaussian_filter(rng.normal(size=(n,n)),20,mode='wrap')
    warp/=(warp.std()*130)
    cord=np.sin(2*np.pi*(9*y+2*x+warp+.27*np.sin(2*np.pi*x)))
    fine=np.sin(2*np.pi*(27*y+3*x+2*warp+.36*np.sin(4*np.pi*x)))
    height=.49+.16*cord+.07*fine+.05*np.cos(2*np.pi*(4*x-y))
    seed=np.zeros_like(x)
    for _ in range(105):
        cx,cy=rng.random(2)
        rx=rng.uniform(.0017,.0065)
        dx=((x-cx+.5)%1-.5)/rx
        dy=((y-cy+.5)%1-.5)/(rx*rng.uniform(.9,2.3))
        q=dx*dx+dy*dy
        seed=np.maximum(seed,np.exp(-q*1.65))
    height-=.29*seed
    dx=(np.roll(height,1,1)-np.roll(height,-1,1))
    dy=(np.roll(height,1,0)-np.roll(height,-1,0))
    data=np.dstack((.5+1.8*dx,.5+1.8*dy,height,seed))
    Image.fromarray(np.uint8(data.clip(0,1)*255)).save(OUT/'glass_cords.png')


def pitch_stamps():
    # Each impression has a pitch and punch number. Fine dropout in the
    # ink exposes the grain beneath it. The same die is frosted onto glass.
    rng=np.random.default_rng(709)
    w,h=192,112
    atlas=Image.new('L',(w*8,h*16))
    face=ImageFont.truetype('DejaVuSerif-Bold.ttf',31)
    numbers=ImageFont.truetype('DejaVuSansMono.ttf',16)
    for midi in range(128):
        tile=Image.new('L',(w,h))
        d=ImageDraw.Draw(tile)
        note=('C','C#','D','D#','E','F','F#','G','G#','A','A#','B')[midi%12]+str(midi//12-1)
        d.text((w/2,7),'L O A M',font=face,anchor='mt',fill=225)
        d.line((21,43,171,43),fill=206,width=2)
        d.polygon([(92,43),(96,39),(100,43),(96,47)],fill=235)
        d.text((w/2,53),note,font=face,anchor='mt',fill=245)
        d.text((w/2,84),f'No. {midi:03}',font=numbers,anchor='mt',fill=223)
        wear=gaussian_filter(rng.random((h,w)),.8)
        ink=np.array(tile)*np.clip(wear*2.3-.14,.15,1)
        atlas.paste(Image.fromarray(ink.astype('uint8')),((midi%8)*w,(midi//8)*h))
    atlas.save(OUT/'pitch_stamps.png')


def board_surface():
    """Oil, open vessels, dents and scraper tracks in a 32 cm square sample."""
    rng=np.random.default_rng(51317)
    n=1024
    noise=rng.normal(size=(n,n))
    def field(radius):
        a=gaussian_filter(noise,radius,mode='wrap')
        return np.clip(.5+.18*a/a.std(),0,1)
    oil=.66*field(40)+.34*field((4,27))
    pores=np.zeros_like(oil)
    scars=np.zeros_like(oil)
    def impression(plane,rx,ry,angle,strength):
        cx,cy=rng.integers(n,size=2)
        extent=int(max(rx,ry)*2)+1
        iy,ix=np.mgrid[-extent:extent+1,-extent:extent+1]
        u=(ix*np.cos(angle)+iy*np.sin(angle))/rx
        v=(iy*np.cos(angle)-ix*np.sin(angle))/ry
        stamp=strength*np.exp(-1.8*(u*u+v*v))
        loc=np.ix_((cy+iy[:,0])%n,(cx+ix[0,:])%n)
        plane[loc]=np.maximum(plane[loc],stamp)
    for _ in range(5100):
        impression(pores,rng.uniform(3,14),rng.uniform(.6,2.0),rng.normal(0,.055),rng.uniform(.3,1.))
    for _ in range(180):
        impression(scars,rng.uniform(3,17),rng.uniform(1,6),rng.uniform(-2,2),rng.uniform(.2,.9))
    for _ in range(48):
        impression(scars,rng.uniform(12,72),rng.uniform(.8,1.8),rng.normal(.95,.40),rng.uniform(.35,1.))
    data=np.dstack((pores,scars,oil,field((1.3,10))))
    Image.fromarray(np.uint8(data.clip(0,1)*255)).save(OUT/'board_surface.png')


if __name__=='__main__':
    furnace_glass()
    pitch_stamps()
    board_surface()
