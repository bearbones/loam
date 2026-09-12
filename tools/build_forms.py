"""Prepare renderer-independent mesh recipes from an exported geometry manifest."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from formlab.recipes import harp_frame,soundboard,action_plate,branching_stand,pack,STYLES
ROOT=Path(__file__).resolve().parents[1]
layout_path=Path(sys.argv[1] if len(sys.argv)>1 else ROOT/'harness/assets/clockwork.json')
out=Path(sys.argv[2] if len(sys.argv)>2 else ROOT/'render/form-study/recipe.json')
layout=json.loads(layout_path.read_text()); objects=[]
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
out.parent.mkdir(exist_ok=True,parents=True)
out.write_text(json.dumps(dict(format='formlab/1',source_layout=str(layout_path),objects=objects),separators=(',',':')))
print('FORMS: PASS;',len(objects),'assemblies;',sum(len(o['pieces']) for o in objects),'closed analytic components;',out)
