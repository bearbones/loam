"""Verify functional ferrule caps are buried in their receiving backbone."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from mesh_distance import ClosedSurface
from mathutils import Vector
r=json.load(open(ROOT/'render/form-study/recipe.json'))
for obj in r['objects']:
 if not obj['name'].endswith('_carved'):continue
 m=obj['pieces'][0];tree=ClosedSurface(m['vertices'],m['faces'])
 ds=[tree.signed_distance(Vector(p['path'][-1])) for p in obj['pieces'][1:]]
 assert max(ds)<-.01, (obj['name'], 'exposed ferrule cap')
 print(obj['name'],'RECEIVER CAPS PASS: minimum burial',-max(ds),'m')
