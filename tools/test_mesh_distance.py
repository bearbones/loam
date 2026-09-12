"""Independent inside/outside checks for concave and overlapping closed parts."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from mesh_distance import ClosedSurface
from mathutils import Vector
vertices=[];faces=[]
# Two overlapping boxes make a concave L in plan, with internal faces retained.
for dx,dy in ((.5,0),(0,.5)):
    offset=len(vertices)
    vertices += [[x+dx,y+dy,z] for x,y,z in ((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))]
    for q in ((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)):
        faces += [[offset+q[i] for i in t] for t in ((0,1,2),(0,2,3))]
surface=ClosedSurface(vertices,faces)
for p in ((0,0,0),(1.4,0,0),(0,1.4,0)):
    assert surface.signed_distance(Vector(p))<0,p
for p in ((1.4,1.4,0),(5,0,0),(0,0,2)):
    assert surface.signed_distance(Vector(p))>0,p
print('MESH DISTANCE: PASS — concave exterior, interior, overlap and distant points')
