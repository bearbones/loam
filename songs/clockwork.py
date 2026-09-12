#!/usr/bin/env python3
"""An additive arrangement of The Chamber for glass bells and temple blocks.
Reads the original exported performance; never overwrites it. Run after chamber.py.
python3 songs/clockwork.py [original-export-directory] [output-directory]
"""
import json, sys, shutil
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from loam import Take, SR, write_wav, ruler
from loam.score import Score, Instrument, Mechanism, StringDef, Actuator
from loam.space import ir_room, convolve_tail
source=Path(sys.argv[1] if len(sys.argv)>1 else 'render/chamber')
output=Path(sys.argv[2] if len(sys.argv)>2 else 'render/clockwork')
if source.resolve()==output.resolve(): raise ValueError('Expanded output must differ from original')
original=json.loads((source/'score.json').read_text())
mechs=[]
for data in original['instrument']['mechanisms']:
    kw=dict(data); kw['strings']=[StringDef(**s) for s in kw['strings']]; kw['actuators']=[Actuator(**a) for a in kw['actuators']]
    mechs.append(Mechanism(**kw))
bells=Mechanism.build('bells','struck','glass',[74,77,81,86],arms=2,overlap=1,span=.65,pos=[-.6,0,-.85],arm_kind='mallet',approach_s=.14,recover_s=.14,travel_s=.045,length_max=.32)
blocks=Mechanism.build('blocks','struck','wood',[62,69,74],arms=1,span=.55,pos=[.7,0,-.85],arm_kind='hammer',approach_s=.08,recover_s=.08,travel_s=.035,length_max=.22)
canvas=Take(original['duration_s'],original['seed'],tail_s=original['total_s']-original['duration_s'])
score=Score(canvas,'The Clockwork Chamber',original['bpm'],original['seed'],Instrument('clockwork chamber',mechs+[bells,blocks]))
for mid,rel in original['stems'].items():
    rate,x=wavfile.read(source/rel)
    if rate!=SR: raise ValueError('Sample-rate mismatch')
    if np.issubdtype(x.dtype,np.integer): x=x.astype(float)/max(abs(np.iinfo(x.dtype).min),np.iinfo(x.dtype).max)
    score.bus(mid)[:]=x/original['stems_gain']
score.events=[dict(e) for e in original['events']]
score.cues=[dict(c) for c in original['cues']]
# Existing events retain their audio and are globally re-solved with unchanged mechanisms.
beat=60/original['bpm']
for bar in range(8,24):
    if bar%2==0:
        for k,b in enumerate((1.,3.)):
            sid=bells.strings[(bar//2+k)%4].id; t=(bar*4+b)*beat
            assert score.can_play('bells',t,sid)
            score.pluck('bells',t,sid,amp=.17 if k else .22,voice='glass answer')
    for k,b in enumerate((.5,2.,3.5)):
        sid=blocks.strings[(bar+k)%3].id; t=(bar*4+b)*beat
        assert score.can_play('blocks',t,sid)
        score.pluck('blocks',t,sid,amp=.2 if k!=1 else .28,voice='escapement')
for k,b in enumerate((96,100,104,108)):
    score.pluck('bells',b*beat,bells.strings[(3-k)%4].id,amp=.2,voice='glass coda')
newdoc=score.export(str(output))
newdoc['shapes']=original['shapes']
shutil.copyfile(source/original['shapes']['file'],output/original['shapes']['file'])
(output/'score.json').write_text(json.dumps(newdoc,indent=1))
mix=score.mixdown(); wet=convolve_tail(mix,ir_room(t60=2.2,size=1.3,bright=.45,seed=original['seed']),mix=.28)[:canvas.n]
x=sosfilt(butter(2,7500,btype='low',fs=SR,output='sos'),wet,axis=0)
x=np.tanh(x*1.25)/np.tanh(1.25); x*=.9/np.max(np.abs(x))
write_wav(str(output/'chamber.wav'),x)
check=ruler.plan_consistent(score.events)
assert check['ok'] and not check['unassigned'] and not score.conflicts
old_by_id={e['i']:e for e in original['events']}
for e in score.events[:len(original['events'])]:
    old=old_by_id[e['i']]
    for key in ('t','strings','actuator','t_move','t_free','pick','shape'):
        assert e.get(key)==old.get(key),(e['i'],key)
for mid in ('bells','blocks'):
    rec=ruler.score_recall(score.bus(mid),[e['t'] for e in score.events if e['mech']==mid],tol_s=.03,min_sep=.15)
    print(mid,'onset recall',rec['recall']); assert rec['recall']>=.9
print('CLOCKWORK ARRANGEMENT: PASS;',len(score.events)-len(original['events']),'new events; original plans preserved')
