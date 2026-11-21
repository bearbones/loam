"""Overcrank. An original drum feature in 4/4, performed by two hands and two feet.

Run python3 songs/overcrank.py to rebuild the shared score and stereo master.
"""
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from loam import SR, drumkit
from loam.space import ir_room

BPM=148
BEAT=60/BPM
LEAD=1.22
ASSETS=ROOT/'harness/assets'


def compose():
    events=[]
    rng=np.random.default_rng(1907)
    def hit(bar,tick,voice,limb,strength,style=''):
        events.append(dict(t=round(LEAD+(bar*4+tick/12)*BEAT,7),voice=voice,limb=limb,
                           v=round(strength,3),offset=round(rng.uniform(-1,1),4),style=style))
    for tick in (-24,-12):
        hit(0,tick,'hat','left',.39)
    for bar in range(20):
        # A half-time breakdown leaves room to spin a stick while the other
        # hand and both feet hold the pulse. The closing phrase uses sextuplets.
        if bar in (3,7,11,15,18):
            cascade=bar in (11,15,18)
            step=2 if cascade else 3
            for j,tick in enumerate(range(0,48,step)):
                limb='right' if j%2 else 'left'
                voice=('snare' if tick<12 else ('high' if limb=='left' else 'mid') if tick<30
                       else ('snare' if limb=='left' else 'floor'))
                if tick>=36:
                    # Lead back up to the cymbals. The pedal takes the last
                    # pickup so neither hand has to come through a crash from below.
                    voice='high' if limb=='left' else 'mid'
                    if tick>=42:continue
                hit(bar,tick,voice,limb,.96 if j%3==0 else .48+.19*((j+bar)%3))
            for tick in (0,18,30,39,45):hit(bar,tick,'kick','kick',.89 if tick%6==0 else .69)
        elif bar==19:
            for tick in (0,12,24):
                hit(bar,tick,'crash_l','left',1.)
                hit(bar,tick,'crash_r','right',.94)
                hit(bar,tick,'kick','kick',1.)
            # One beat of air before the final double crash.
        elif 8<=bar<11:
            for tick in (0,6,12,18,24,30,36,42):
                hit(bar,tick,'ride','right',.78 if tick%12==0 else .44)
            hit(bar,24,'snare','left',1.)
            if bar==9:hit(bar,42,'high','left',.62)
            for tick in (0,9,18,33,39):hit(bar,tick,'kick','kick',.91 if tick in (0,18) else .64)
            for tick in (12,36):hit(bar,tick,'hat','pedal',.42,'chick')
        elif bar in (4,5,6,12,13,14):
            for tick in (0,6,12,18,24,30,36,42):
                voice='crash_r' if tick==0 and bar in (4,12) else 'ride'
                hit(bar,tick,voice,'right',.85 if tick%12==0 else .56)
            for tick in ((12,21,36,45) if bar%2 else (12,36)):
                hit(bar,tick,'snare','left',.99 if tick%12==0 else .32)
            for tick in ((0,9,18,24,33,42) if bar%2==0 else (0,18,24,30,39,45)):
                hit(bar,tick,'kick','kick',.91 if tick%12==0 else .74)
            for tick in (12,36):hit(bar,tick,'hat','pedal',.48,'chick')
        else:
            for tick in (0,6,12,18,24,30,36,42):
                voice='crash_l' if tick==0 and bar in (0,16) else 'hat'
                hit(bar,tick,voice,'left',.93 if voice=='crash_l' else .72 if tick%12==0 else .52,
                    'open' if voice=='hat' and tick==42 and bar%2==0 else '')
            for tick in ((12,21,36,45) if bar in (1,17) else (12,36)):
                hit(bar,tick,'snare','right',1. if tick%12==0 else .35)
            for tick in ((0,18,24,33,42) if bar%2==0 else (0,9,24,30,39)):
                hit(bar,tick,'kick','kick',.94 if tick%12==0 else .73)
    for voice,limb in [('crash_l','left'),('crash_r','right'),('kick','kick')]:
        hit(20,0,voice,limb,1.)
    events.sort(key=lambda e:e['t'])
    for limb in ('left','right'):
        notes=[e for e in events if e['limb']==limb]
        for i,(prev,nxt) in enumerate(zip(notes,notes[1:])):
            gap=nxt['t']-prev['t']
            if gap>.73:
                nxt['trick']='overhand' if gap>1.3 else 'wheel' if i%3 else 'salute'
    return dict(title='Overcrank',bpm=BPM,lead=LEAD,total_s=round(LEAD+80*BEAT+2.1,6),events=events)


def render(score):
    n=round(score['total_s']*SR)
    mix=np.zeros((n,2))
    hats=[e['t'] for e in score['events'] if e['voice']=='hat' and e['style']!='open']
    for i,e in enumerate(score['events']):
        voice=e['voice'];s=drumkit.hit(voice,e['v'],i,e['style'])
        at=round(e['t']*SR);s=s[:n-at]*drumkit.GAIN[voice]
        if e['style']=='open':
            close=next((t for t in hats if t>e['t']),score['total_s'])
            s*=np.exp(-np.maximum(0.,np.arange(s.size)/SR-(close-e['t']))*75)
        angle=(1+drumkit.PAN[voice])*np.pi/4
        mix[at:at+s.size]+=s[:,None]*[np.cos(angle),np.sin(angle)]
    ir=ir_room(t60=.83,size=.83,bright=.56,seed=24)
    ir/=np.sqrt(np.sum(ir**2,axis=0))
    mono=mix.mean(axis=1)
    for ch in (0,1):
        mix[:,ch]+=.18*fftconvolve(mono,ir[:,ch])[:n]
    mix=np.tanh(mix*1.65)
    mix[-round(.16*SR):]*=np.linspace(1,0,round(.16*SR))[:,None]
    return np.int16(mix*(30500/np.max(np.abs(mix))))


if __name__=='__main__':
    score=compose()
    out=ROOT/'render/overcrank';out.mkdir(parents=True,exist_ok=True)
    drumkit.export_sfz(out/'overcrank-kit.zip')
    wav=out/'overcrank.wav'
    wavfile.write(wav,SR,render(score))
    subprocess.run(['ffmpeg','-nostdin','-loglevel','error','-y','-i',str(wav),
                    '-c:a','libvorbis','-q:a','6',str(ASSETS/'overcrank.ogg')],check=True,timeout=50)
    (ASSETS/'overcrank.json').write_text(json.dumps(score,separators=(',',':'))+'\n')
    print(len(score['events']),'hits,',score['total_s'],'seconds')
