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
from formlab.recipes import harp_frame,soundboard,action_plate,neck_faces,bar_frame,bench_frame,pack,STYLES
from formlab.layout import bar_frame_plan,bench_plan,bench_elements,neck_plan
from formlab.linkage import parallelogram_arm,pick_tool,mallet_tool,hammer_tool,tool_mount
from formlab.hand import hand_tool,HAND_SPEC
from formlab.rig import Rig,HAMMER
from formlab.clearance import choose_offset,report,cross_arm_clearance,pinion_mount,rail_keep_clear,bar_pair_separation,drive_kind
from formlab.gantry import plan_gantries, rack as gantry_rack
from formlab import pawl as pawl_lib
from formlab import drives as drives_lib
ROOT=Path(__file__).resolve().parents[1]
layout_path=Path(sys.argv[1] if len(sys.argv)>1 else ROOT/'harness/assets/clockwork.json')
out=Path(sys.argv[2] if len(sys.argv)>2 else ROOT/'render/form-study/recipe.json')
layout=json.loads(layout_path.read_text()); objects=[]; neck={}; form_masses={}
score_path=Path(sys.argv[3]) if len(sys.argv)>3 else Path(layout.get('score',ROOT/'render/chamber/score.json'))
for mid in ('harp','rake'):
    elements=[dict(s,id=sid) for sid,s in layout['strings'].items() if s['mid']==mid]
    if not elements: continue
    # The neck's hardware follows the carved neck's real faces (recipes.neck_faces);
    # the builder places it and the strings' dead lengths from this block.
    for sid,f in neck_faces(elements).items():
        neck[sid]=neck_plan(layout['strings'][sid]['b'],f['face'],f['back'],discs=mid=='harp')
    for style in STYLES:
        pieces=harp_frame(elements,style)
        objects.append(pack(f'form_{mid}_{style}',pieces,'brass' if style=='ribbed' else 'wood',
            'geometric traditional frame with coved moulding'))
        objects[-1]['finish']='profiled'; form_masses[objects[-1]['name']]=objects[-1]['mass_kg']
    objects.append(pack(f'form_{mid}_soundboard',soundboard(elements),'spruce','geometric inset soundboard'))
    objects[-1]['finish']='profiled'; form_masses[objects[-1]['name']]=objects[-1]['mass_kg']
    if mid=='harp':
        objects.append(pack('form_harp_actionplate',action_plate(elements),'brass','static neck mechanism mounting plate'))
        objects[-1]['finish']='profiled'; form_masses[objects[-1]['name']]=objects[-1]['mass_kg']
# The bar instrument's frame: rails under the nodal lines on end frames (formlab.layout.bar_frame_plan).
objects.append(pack('form_bars_stand',bar_frame(bar_frame_plan([s for s in layout['strings'].values() if s['mid']=='bars'])),'wood',
    'mallet-instrument construction: node-line rails, end frames, stretcher, name board')); objects[-1]['finish']='profiled'; form_masses[objects[-1]['name']]=objects[-1]['mass_kg']
# Every other struck instrument sits on a trestle bench (formlab.layout.bench_plan).
for mid,mech in layout['mechanisms'].items():
    if mech['kind']!='struck' or mid=='bars': continue
    els=bench_elements([dict(s,id=sid) for sid,s in layout['strings'].items() if s['mid']==mid],mech['material'])
    objects.append(pack(f'form_{mid}_stand',bench_frame(bench_plan(els)),'wood','trestle bench: rails, bearers, splayed legs, ties, stretcher, fascia')); objects[-1]['finish']='profiled'; form_masses[objects[-1]['name']]=objects[-1]['mass_kg']

# Articulated arms: a double parallelogram per actuator, offsets from the motion.
arms={}; reports={}; all_poses={}
if score_path.exists() and layout.get('arms'):
    rig=Rig(json.loads(score_path.read_text()),layout); times=rig.sample_times()
    probe=parallelogram_arm(1.0,1.0,[0,-.11,0],[0,0,-.11]); layers,spec=probe['layers'],probe['spec']
    for aid,cfg in layout['arms'].items():
        poses=rig.poses(aid,times)
        # A stepped arm is driven by rack and pinion, a servo arm by a leadscrew
        # (formlab.clearance.drive_kind, docs/plans/leadscrew-servo-drive.md).
        drive=drive_kind(cfg)
        # The rail planner (formlab.layout_search) has already chosen the offsets and the
        # pinion's mount for this rail; keep them (its 30 Hz screen and this 120 Hz pass can
        # break an offset tie differently). Bare layouts get the same rules applied here: the
        # carriage's second-bar boss keeps off the guide bars, the pinion off the links.
        if 'o1' in cfg and 'pinion' in cfg:
            o1=np.asarray(cfg['o1'],float); o2=np.asarray(cfg['o2'],float); pmount=cfg['pinion']
            sep1=float(bar_pair_separation(poses,o1,'upper').min()); sep2=float(bar_pair_separation(poses,o2,'lower').min())
        else:
            o1,sep1,_=choose_offset(poses,'upper',.11,keep_clear=rail_keep_clear()); o2,sep2,_=choose_offset(poses,'lower',.11)
            pmount,_=pinion_mount(poses,o1,o2,layers,spec,drive=drive)
        parts=parallelogram_arm(float(cfg['l1']),float(cfg['l2']),o1,o2,mount=pmount,drive=drive)
        # A stepped (mallet) arm's pinion carries a roller detent pawl (formlab.pawl): its
        # bracket and pin are cast onto the carriage; the pawl itself is a local part.
        pawl_info=pawl_lib.manifest(pmount,float(rig.contact(rig.acts[aid]['home'])[0])) if rig.stepped(aid) and pawl_lib.MOUNTS[pmount][1] else None
        if pawl_info: parts['carriage']['pieces']=parts['carriage']['pieces']+pawl_lib.bracket_pieces(pmount)
        # PLAYERS M4 carriage-mounted drives: shoulder sector gear + driver pinion,
        # elbow four-bar crank + coupler rod, and a motor housing on a rack carriage's pinion axle.
        s_drv=drives_lib.shoulder_drive_pieces()
        e_drv=drives_lib.elbow_drive_pieces(float(cfg['l1']))
        parts['carriage']['pieces']=parts['carriage']['pieces']+s_drv['carriage']+(drives_lib.pinion_motor_pieces(pmount) if drive=='rack' else [])
        parts['lower']['pieces']=parts['lower']['pieces']+e_drv['lower']
        parts['shoulder_sector']=dict(pieces=s_drv['shoulder_sector'])
        parts['shoulder_pinion']=dict(pieces=s_drv['shoulder_pinion'])
        parts['elbow_crank']=dict(pieces=e_drv['elbow_crank'])
        parts['elbow_rod']=dict(pieces=e_drv['elbow_rod'])
        # PLAYERS M5 hinged mallet shaft + four-bar wrist crank, and hammer lift cam:
        if cfg['kind']=='mallet':
            w_drv=drives_lib.wrist_drive_pieces(rig.flip_sign(aid))
            parts['wristhead']['pieces']=parts['wristhead']['pieces']+w_drv['wristhead']
            parts['wrist_shaft']=dict(pieces=w_drv['wrist_shaft'])
            parts['wrist_crank']=dict(pieces=w_drv['wrist_crank'])
            parts['wrist_rod']=dict(pieces=w_drv['wrist_rod'])
        elif cfg['kind']=='hammer':
            parts['hammer_cam']=dict(pieces=drives_lib.hammer_cam_pieces(rig.rest_angle(aid),rig.flip_sign(aid)))
        strings={sid:s for sid,s in layout['strings'].items() if s['mid']==cfg['mid']}
        rep=report(rig,aid,o1,o2,layers,spec,strings,poses=poses,mount=pmount,drive=drive); reports[aid]=rep
        material={'carriage':'steel','elbowhead':'steel','wristhead':'steel','shoulder':'steel','elbow':'steel','wrist':'steel',
                  'shoulder_sector':'brass','shoulder_pinion':'brass','elbow_crank':'steel','elbow_rod':'brass',
                  'wrist_shaft':'rose','wrist_crank':'steel','wrist_rod':'brass','hammer_cam':'brass'}
        arm_masses={}
        for part,body in parts.items():
            if part in ('layers','spec'): continue
            # a piece may name its own material (the leadscrew nut is bronze on a steel carriage)
            mats=[getattr(p,'material',material.get(part,'brass')) for p in body['pieces']]
            entry=pack(f'{aid}__{part}',body['pieces'],material.get(part,'brass'),'articulated link, local frame',materials=mats if len(set(mats))>1 else None)
            entry['finish']='profiled'; entry['local']=True; objects.append(entry); arm_masses[part]=entry['mass_kg']
        # The tool hangs from the wrist crosshead's lower boss; the shank is built to reach it.
        mount=tool_mount(rig.wrist_offset(cfg),o2)
        kind=cfg['kind']; head_mats=None; head_info=None
        if kind=='hammer':
            # A hinged hammer's head is a THIRD part with its own origin at the
            # hinge, because it turns on its own (formlab.rig.head_angle); the
            # rest angle and the side it lies back on are what place its check.
            tool,tool_mats,head_mats=hammer_tool(mount,rig.rest_angle(aid),rig.flip_sign(aid))
            head_info=dict(hinge=[0,round(float(HAMMER['head_l']),5),0],length=float(HAMMER['head_l']),
                           rest_angle=round(float(rig.rest_angle(aid)),9),sign=float(rig.flip_sign(aid)))
        elif kind=='mallet': tool,tool_mats=mallet_tool(mount),None
        elif kind=='pick':
            tool=hand_tool(mount,side_sign=1.0 if int(cfg.get('index',0))!=1 else -1.0)
            tool_mats=['horn']+['brass']*(len(tool[0])-1)
        else:
            tool=pick_tool(mount); tool_mats=['horn']+['brass']*(len(tool[0])-1)
        # a plectrum is horn (the blade, first piece) in a brass ferrule with brass screws
        objects.append(pack(f'{aid}__tool',tool[0],{'mallet':'felt','hammer':'steel'}.get(kind,'brass'),
                            'contact tool, origin at contact',materials=tool_mats))
        objects[-1]['finish']='profiled'; objects[-1]['local']=True; arm_masses['tool']=objects[-1]['mass_kg']
        objects.append(pack(f'{aid}__shank',tool[1],'steel','tool shank to its socket on the wrist crosshead'))
        objects[-1]['finish']='profiled'; objects[-1]['local']=True; arm_masses['shank']=objects[-1]['mass_kg']
        if head_info:
            objects.append(pack(f'{aid}__head',tool[2],'felt',
                                'hinged hammer head, local frame at its hinge, built at the blow',materials=head_mats))
            objects[-1]['finish']='profiled'; objects[-1]['local']=True; arm_masses['head']=objects[-1]['mass_kg']
        if pawl_info:
            lever,mats=pawl_lib.lever_pieces(pmount)
            objects.append(pack(f'{aid}__pawl',lever,'steel','roller detent pawl riding the pinion, local frame at its pivot',materials=mats))
            objects[-1]['finish']='profiled'; objects[-1]['local']=True; arm_masses['pawl']=objects[-1]['mass_kg']
            drum,mats=pawl_lib.roller_pieces(pmount)
            objects.append(pack(f'{aid}__roller',drum,'steel','the pawl\'s roller, local frame on its axle',materials=mats))
            objects[-1]['finish']='profiled'; objects[-1]['local']=True; arm_masses['roller']=objects[-1]['mass_kg']
        upper=np.concatenate([m.vertices for m in parts['upper']['pieces']])
        arms[aid]=dict(o1=o1.round(5).tolist(),o2=o2.round(5).tolist(),layers=layers,
            link_extent_y=float(upper[:,1].max()-upper[:,1].min()),
            oil_cups=[dict(part=p,**parts[p]['cup']) for p in ('upper','lower') if parts[p].get('cup')],
            upper_pair_separation_m=float(sep1),lower_pair_separation_m=float(sep2),
            self_clearance_m=rep['worst_gap_m'],self_worst=rep['worst_pair'],self_worst_time_s=rep['worst_time_s'],
            string_clearance_m=rep['string_gap_m'],string_worst=list(rep['string_worst']))
        all_poses[aid]=poses; layout['arms'][aid].update(o1=arms[aid]['o1'],o2=arms[aid]['o2'],layers=layers,pinion=pmount,drive=drive)
        arms[aid]['pinion']=pmount; arms[aid]['drive']=drive
        if pawl_info: arms[aid]['pawl']=pawl_info; layout['arms'][aid]['pawl']=pawl_info
        if head_info:
            arms[aid]['head']=head_info; layout['arms'][aid]['head']=head_info
            arms[aid]['head_l']=float(HAMMER['head_l'])
            arms[aid]['hammer']=dict(HAMMER,rest_angle=round(float(rig.rest_angle(aid)),9))
            layout['arms'][aid]['head_l']=arms[aid]['head_l']
            layout['arms'][aid]['hammer']=arms[aid]['hammer']
        elif kind=='mallet':
            arms[aid]['head_l']=float(drives_lib.WRIST_DRIVE['shaft_l'])
            layout['arms'][aid]['head_l']=arms[aid]['head_l']
        elif kind=='pick':
            arms[aid]['hand']=dict(HAND_SPEC,side_sign=1.0 if int(cfg.get('index',0))!=1 else -1.0)
            layout['arms'][aid]['hand']=arms[aid]['hand']
        arms[aid]['limits']=drives_lib.joint_limits(layout['arms'][aid],poses)
        arms[aid]['drives']=drives_lib.manifest_drives(layout['arms'][aid])
        arms[aid]['masses']=arm_masses
    # Rail gantries: heads, masts, plinths and (where needed) brackets, placed clear of everything above.
    form_boxes=[(o['name'],(V.min(0),V.max(0))) for o in objects if not o.get('local')
                for V in [np.concatenate([np.array(p['vertices']) for p in o['pieces']])]]
    for aid,g in plan_gantries(layout,all_poses,form_boxes).items():
        cfg=layout['arms'][aid]
        if drive_kind(cfg)=='rack':
            # Separate the rack into its own form (`form_<aid>_rack`, with teeth
            # phase-aligned to the pinion's seating phase) so Godot attaches it to
            # the guide-bar sag node (`shudder_nodes[aid]['bars']`).
            n_rack=len(gantry_rack(cfg))
            phase=float(cfg.get('pawl',{}).get('phase',0.0))
            head_brass=g['brass'][n_rack:]
            rack_pcs=drives_lib.rack_pieces(cfg,phase)
            objects.append(pack(f'form_{aid}_railhead',head_brass,'brass','rail heads and brackets capturing the guide bars')); objects[-1]['finish']='profiled'
            arms[aid]['masses']['railhead']=objects[-1]['mass_kg']
            objects.append(pack(f'form_{aid}_rack',rack_pcs,'brass','phase-aligned toothed rack carried on the guide bars')); objects[-1]['finish']='profiled'
            arms[aid]['masses']['rack']=objects[-1]['mass_kg']
            g['rack']['phase']=round(phase,9); g['rack']['form']=f'form_{aid}_rack'
        else:
            objects.append(pack(f'form_{aid}_railhead',g['brass'],'brass','rail heads and brackets capturing the guide bars; leadscrew bearings')); objects[-1]['finish']='profiled'
            arms[aid]['masses']['railhead']=objects[-1]['mass_kg']
        objects.append(pack(f'form_{aid}_gantry',g['steel'],'steel','tapered mast, plinth, knee brace, bolts')); objects[-1]['finish']='profiled'
        arms[aid]['masses']['gantry']=objects[-1]['mass_kg']
        arms[aid]['gantry']=dict(ends=g['ends'],margin_m=g['margin'],worst=g['worst'],rack=g['rack'])
        # a servo arm's leadscrew shaft is its own form: Godot spins it about its axis
        if g.get('shaft'):
            shaft_multi=drives_lib.screw_shaft_multi(cfg)
            objects.append(pack(f'form_{aid}_screw',shaft_multi,'steel','multi-start leadscrew shaft and thread, turning in the heads\' bearings')); objects[-1]['finish']='profiled'
            arms[aid]['masses']['screw']=objects[-1]['mass_kg']
            arms[aid]['screw']=dict(g['screw'],starts=drives_lib.SCREW_STARTS,lead=drives_lib.SCREW_LEAD)
    cross={f'{a}/{b}':dict(gap_m=g,parts=list(pair),time_s=float(times[k])) for (a,b),(g,pair,k) in cross_arm_clearance(reports).items()}
    worst_cross=min(cross.values(),key=lambda c:c['gap_m']) if cross else None
    arms['_cross_arm']=cross
    for aid,a in arms.items():
        if aid.startswith('_'): continue
        if min(a['self_clearance_m'],a['string_clearance_m'])<0: raise SystemExit(f'ARM CLEARANCE FAIL {aid}: {a}')
        if a['gantry']['margin_m']<0: raise SystemExit(f'GANTRY CLEARANCE FAIL {aid}: {a["gantry"]}')
    if worst_cross and worst_cross['gap_m']<0: raise SystemExit(f'CROSS-ARM CLEARANCE FAIL {worst_cross}')
out.parent.mkdir(exist_ok=True,parents=True)
out.write_text(json.dumps(dict(format='formlab/1',source_layout=str(layout_path),objects=objects,arms=arms,neck=neck,masses=form_masses),separators=(',',':')))
print('FORMS: PASS;',len(objects),'assemblies;',sum(len(o['pieces']) for o in objects),'closed analytic components;',out)
for aid,a in arms.items():
    if aid.startswith('_'): continue
    print('  ARM',aid,'pair sep %.3f/%.3f m; self %.3f m (%s); string %.3f m (%s)'%(a['upper_pair_separation_m'],a['lower_pair_separation_m'],a['self_clearance_m'],'/'.join(a['self_worst']),a['string_clearance_m'],a['string_worst'][0]))
if arms.get('_cross_arm'):
    w=min(arms['_cross_arm'].items(),key=lambda kv:kv[1]['gap_m']); print('  CROSS-ARM worst %s %.3f m %s @%.2fs'%(w[0],w[1]['gap_m'],'/'.join(w[1]['parts']),w[1]['time_s']))
