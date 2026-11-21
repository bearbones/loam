"""Overcrank trap kit. Three deterministic takes of each of eleven articulations."""
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

from . import SR, drums
from .membrane import fddrum

# Instrument names also identify the physical surfaces in the scene.
PAN={'kick':0,'snare':.10,'high':.21,'mid':-.17,'floor':-.53,'ride':-.48,'crash_r':-.43,'crash_l':.55,'hat':.48}
GAIN={'kick':1.02,'snare':.95,'high':.77,'mid':.81,'floor':.87,'ride':.47,'crash_r':.75,'crash_l':.77,'hat':.52}
KEYS=((36,'kick',''),(38,'snare',''),(50,'high',''),(47,'mid',''),(43,'floor',''),
      (42,'hat',''),(46,'hat','open'),(44,'hat','chick'),(51,'ride',''),(49,'crash_l',''),(57,'crash_r',''))


def _bronze(voice,variant):
    dur={'ride':1.12,'crash_l':2.08,'crash_r':1.76}[voice]
    rng=np.random.default_rng(517+variant+{'ride':0,'crash_l':21,'crash_r':45}[voice])
    t=np.arange(int(dur*SR))/SR
    crash=voice!='ride'
    # Dispersed flexural modes under a broadband wash. The ride retains its ping.
    modes=np.zeros_like(t)
    for f in np.geomspace(384 if crash else 498,11200,44)*rng.uniform(.91,1.09,44):
        env=np.exp(-t*(3.2/dur+.00044*f))
        modes+=np.sin(2*np.pi*f*t+rng.uniform(0,6.28))*env/(1+f/4400)
    sos=butter(2,[3600 if crash else 4300,14800],btype='bandpass',fs=SR,output='sos')
    wash=sosfilt(sos,rng.normal(size=t.size))
    sound=modes*(.14 if crash else .22)+wash*(1.40 if crash else .54)*np.exp(-t*(2.9/dur))
    if not crash:sound+=.88*np.sin(t*(2*np.pi*2530))*np.exp(-t*17)
    sound*=np.minimum(t/.0013,1)*np.minimum((dur-t)/.032,1)
    return sound/max(abs(sound))


@lru_cache(maxsize=None)
def _membrane(voice,variant):
    freq={'high':172,'mid':130,'floor':89,'snare':202}[voice]*(.993+variant*.004)
    m=fddrum(freq,.48,load=0.,strike=(.37+variant*.017,.09),N=31)
    return m/max(1e-8,max(abs(m)))


@lru_cache(maxsize=None)
def _sample(voice,style,variant):
    if voice in ('ride','crash_l','crash_r'):return _bronze(voice,variant)
    if voice=='kick':return drums.kick(f0=137,f1=49,drop=26,drive=1.55,click=.48,seed=13+variant)
    if voice=='hat':
        if style=='chick':return drums.hat(.061,seed=variant+44)*.65
        return drums.hat(.093,open_=style=='open',seed=variant+20)
    skin=_membrane(voice,variant)
    if voice=='snare':
        sound=drums.snare(.255,186+variant*2,1.05,seed=variant+11)
        sound+=skin[:len(sound)]*.40
    else:
        sound=drums.tom({'high':163,'mid':125,'floor':84}[voice],.48,seed=variant)
        sound+=skin[:len(sound)]*.62
    return sound/np.max(np.abs(sound))


def hit(voice: str, velocity: float = 1.0, take: int = 0, articulation: str = '') -> np.ndarray:
    """Return a mono strike at 44.1 kHz. Hat articulations are '', 'open' and 'chick'."""
    if voice not in GAIN:
        raise ValueError(f'unknown drum voice {voice!r}')
    if articulation not in (('', 'open', 'chick') if voice=='hat' else ('',)):
        raise ValueError(f'unknown {voice} articulation {articulation!r}')
    if not 0<=velocity<=1:
        raise ValueError('velocity must be in [0,1]')
    return _sample(voice,articulation,take%3)*velocity**1.4


def export_sfz(path: Path) -> None:
    """Write a portable GM-mapped kit with rotating takes and a choked hi-hat."""
    regions=[]
    def write(archive,name,data):
        info=ZipInfo(name)
        info.compress_type=ZIP_DEFLATED
        archive.writestr(info,data)
    with ZipFile(path,'w') as archive:
        for key,voice,style in KEYS:
            name=voice+'_'+(style or 'closed') if voice=='hat' else voice
            choke=' group=1 off_by=1 off_mode=fast' if voice=='hat' else ''
            gain=20*np.log10(GAIN[voice])
            regions.append(f'<group> key={key} pitch_keycenter={key} loop_mode=one_shot seq_length=3 pan={PAN[voice]*100:.0f} volume={gain:.2f}{choke}')
            for take in range(3):
                filename=f'samples/{name}-{take+1}.wav'
                wave=BytesIO()
                wavfile.write(wave,SR,np.int16(np.clip(hit(voice,take=take,articulation=style),-1,1)*32760))
                write(archive,filename,wave.getvalue())
                regions.append(f'<region> seq_position={take+1} sample={filename}')
        write(archive,'Overcrank.sfz',('\n'.join(regions)+'\n').encode('utf-8'))
