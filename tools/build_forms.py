"""Prepare renderer-independent mesh recipes from an exported geometry manifest.

    python3 tools/build_forms.py LAYOUT.json RECIPE.json [SCORE.json]

Frames, soundboards, plates and the bar stand are world-space objects. The
articulated arm parts are LOCAL objects (one recipe entry per moving part in
its own link frame, see formlab.linkage) that Blender assembles at the home
pose and Godot poses every frame; their parallelogram offsets are chosen here
from the score's actual motion (formlab.clearance) and handed back through
the recipe's `arms` block for the manifest.
"""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from formlab.recipes import harp_frame,soundboard,action_plate,branching_stand,pack,STYLES
from formlab.linkage import parallelogram_arm,pick_tool,mallet_tool,tool_mount
from formlab.rig import Rig
from formlab.clearance import choose_offset,report,cross_arm_clearance
from formlab.gantry import plan_gantries
ROOT=Path(__file__).resolve().parents[1]
layout_path=Path(sys.argv[1] if len(sys.argv)>1 else ROOT/'harness/assets/clockwork.json')
out=Path(sys.argv[2] if len(sys.argv)>2 else ROOT/'render/form-study/recipe.json')
layout=json.loads(layout_path.read_text()); objects=[]
score_path=Path(sys.argv[3]) if len(sys.argv)>3 else Path(layout.get('score',ROOT/'render/chamber/score.json'))
for mid in ('harp','rake'):
    elements=[s for s in layout['strings'].values() if s['mid']==mid]
    for style in STYLES:
        pieces=harp_frame(elements,style)
        objects.append(pack(f'form_{mid}_{style}',pieces,'brass' if style=='ribbed' else 'wood',
            'geometric traditional frame with coved moulding'))
        objects[-1]['finish']='profiled'
    objects.append(pack(f'form_{mid}_soundboard',soundboard(elements),'spruce','geometric inset soundboard'))
    objects[-1]['finish']='profiled'
    if mid=='harp':
        objects.append(pack('form_harp_actionplate',action_plate(elements),'brass','static neck mechanism mounting plate'))
        objects[-1]['finish']='profiled'
m=layout['mechanisms']['bars']; xs=[s['a'][0] for s in layout['strings'].values() if s['mid']=='bars']
objects.append(pack('form_bars_stand',branching_stand(m['center'],max(xs)-min(xs)),'wood','load-collection heuristic'))

# Articulated arms: a double parallelogram per actuator, offsets from the motion.
arms={}; reports={}; all_poses={}
if score_path.exists() and layout.get('arms'):
    rig=Rig(json.loads(score_path.read_text()),layout); times=rig.sample_times()
    probe=parallelogram_arm(1.0,1.0,[0,-.11,0],[0,0,-.11]); layers,spec=probe['layers'],probe['spec']
    for aid,cfg in layout['arms'].items():
        poses=rig.poses(aid,times)
        o1,sep1,_=choose_offset(poses,'upper',.11); o2,sep2,_=choose_offset(poses,'lower',.11)
        # keep the offsets readable: snap to the nearest 5 degrees of the same magnitude
        parts=parallelogram_arm(float(cfg['l1']),float(cfg['l2']),o1,o2)
        strings={sid:s for sid,s in layout['strings'].items() if s['mid']==cfg['mid']}
        rep=report(rig,aid,o1,o2,layers,spec,strings,poses=poses); reports[aid]=rep
        material={'carriage':'steel','elbowhead':'steel','wristhead':'steel','shoulder':'steel','elbow':'steel','wrist':'steel'}
        for part,body in parts.items():
            if part in ('layers','spec'): continue
            entry=pack(f'{aid}__{part}',body['pieces'],material.get(part,'brass'),'articulated link, local frame')
            entry['finish']='profiled'; entry['local']=True; objects.append(entry)
        # The tool hangs from the wrist crosshead's lower boss; the shank is built to reach it.
        mount=tool_mount(rig.wrist_offset(cfg),o2)
        tool=mallet_tool(mount) if cfg['kind']=='mallet' else pick_tool(mount)
        objects.append(pack(f'{aid}__tool',tool[0],'felt' if cfg['kind']=='mallet' else 'brass','contact tool, origin at contact'))
        objects[-1]['finish']='profiled'; objects[-1]['local']=True
        objects.append(pack(f'{aid}__shank',tool[1],'steel','tool shank to its socket on the wrist crosshead'))
        objects[-1]['finish']='profiled'; objects[-1]['local']=True
        upper=np.concatenate([m.vertices for m in parts['upper']['pieces']])
        arms[aid]=dict(o1=o1.round(5).tolist(),o2=o2.round(5).tolist(),layers=layers,
            link_extent_y=float(upper[:,1].max()-upper[:,1].min()),
            upper_pair_separation_m=float(sep1),lower_pair_separation_m=float(sep2),
            self_clearance_m=rep['worst_gap_m'],self_worst=rep['worst_pair'],self_worst_time_s=rep['worst_time_s'],
            string_clearance_m=rep['string_gap_m'],string_worst=list(rep['string_worst']))
        all_poses[aid]=poses; layout['arms'][aid].update(o1=arms[aid]['o1'],o2=arms[aid]['o2'],layers=layers)
    # Rail gantries: heads, masts, plinths and (where needed) brackets, placed clear of everything above.
    form_boxes=[(o['name'],(V.min(0),V.max(0))) for o in objects if not o.get('local')
                for V in [np.concatenate([np.array(p['vertices']) for p in o['pieces']])]]
    for aid,g in plan_gantries(layout,all_poses,form_boxes).items():
        objects.append(pack(f'form_{aid}_railhead',g['brass'],'brass','rail head and bracket capturing the guide bars')); objects[-1]['finish']='profiled'
        objects.append(pack(f'form_{aid}_gantry',g['steel'],'steel','tapered mast, plinth, knee brace, bolts')); objects[-1]['finish']='profiled'
        arms[aid]['gantry']=dict(ends=g['ends'],margin_m=g['margin'],worst=g['worst'])
    cross={f'{a}/{b}':dict(gap_m=g,parts=list(pair),time_s=float(times[k])) for (a,b),(g,pair,k) in cross_arm_clearance(reports).items()}
    worst_cross=min(cross.values(),key=lambda c:c['gap_m']) if cross else None
    arms['_cross_arm']=cross
    for aid,a in arms.items():
        if aid.startswith('_'): continue
        if min(a['self_clearance_m'],a['string_clearance_m'])<0: raise SystemExit(f'ARM CLEARANCE FAIL {aid}: {a}')
        if a['gantry']['margin_m']<0: raise SystemExit(f'GANTRY CLEARANCE FAIL {aid}: {a["gantry"]}')
    if worst_cross and worst_cross['gap_m']<0: raise SystemExit(f'CROSS-ARM CLEARANCE FAIL {worst_cross}')
out.parent.mkdir(exist_ok=True,parents=True)
out.write_text(json.dumps(dict(format='formlab/1',source_layout=str(layout_path),objects=objects,arms=arms),separators=(',',':')))
print('FORMS: PASS;',len(objects),'assemblies;',sum(len(o['pieces']) for o in objects),'closed analytic components;',out)
for aid,a in arms.items():
    if aid.startswith('_'): continue
    print('  ARM',aid,'pair sep %.3f/%.3f m; self %.3f m (%s); string %.3f m (%s)'%(a['upper_pair_separation_m'],a['lower_pair_separation_m'],a['self_clearance_m'],'/'.join(a['self_worst']),a['string_clearance_m'],a['string_worst'][0]))
if arms.get('_cross_arm'):
    w=min(arms['_cross_arm'].items(),key=lambda kv:kv[1]['gap_m']); print('  CROSS-ARM worst %s %.3f m %s @%.2fs'%(w[0],w[1]['gap_m'],'/'.join(w[1]['parts']),w[1]['time_s']))
