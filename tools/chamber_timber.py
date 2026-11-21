"""Cabinet joinery and board-local, metric grain coordinates for the chamber."""
import math
import zlib
import bpy
import numpy as np
from acoustic_bodies import blank, finish, loft, subtract, vec
from layout import bar_frame_plan, board_z, BOARD

TIMBER={'Rosewood','Spruce soundboard','Spruce interior','Oiled walnut'}


def bowtie(name,x,y,z,w,l,material):
    outline=[(-w,-l),(w,-l),(.45*w,0),(w,l),(-w,l),(-.45*w,0)]
    return loft(name,[[(x+a,h,z+b) for a,b in outline] for h in (y-.012,y+.0004)],material)


def cabinet():
    old=bpy.data.objects['Chamber cabinet']
    bpy.data.objects.remove(old,do_unlink=True)
    material='Oiled walnut'
    cases=[]
    def board(name,pos,size,bevel):
        obj=finish(blank(name,pos,size,material),bevel)
        cases.append(obj)
        return obj
    lid=board('Case lid',(0,.877,-1.6),(3.62,.076,.672),.008)
    board('Case base',(0,.104,-1.60),(3.60,.078,.653),.007)
    for side in (-1,1):
        board('Case cheek',(side*1.757,.49,-1.603),(.082,.702,.638),.005)
    for i in range(7):
        x=(i-3)*.495
        board('Rebated back plank',(x,.492,-1.908),(.4945,.704,.035),.0015)
    for y in (.198,.806):
        board('Grille rail',(0,y,-1.302),(3.44,.105,.052),.004)
    # A split runs in from the end of the lid. Two cross-grain keys bridge
    # its cheeks. The keystone outlines are actually recessed into the lid.
    crack=[(-1.815,-.001),(-1.47,.005),(-1.19,-.003),(-.91,0),(-1.19,.002),(-1.47,.012),(-1.815,.010)]
    z=-1.46
    subtract(lid,loft('Shrinkage check',[[(a,h,z+b) for a,b in crack] for h in (.903,.925)],material))
    for i,x in enumerate((-1.58,-1.23)):
        key=bowtie('Inlaid repair key',x,.915,z+.005,.029-i*.003,.058-i*.007,'Rosewood')
        subtract(lid,bowtie('Key mortise',x,.9148,z+.005,.029-i*.003,.058-i*.007,material))
        cases.append(finish(key,.0006))
    # Wedged ends of the front rails are visible through the cheek.
    for side in (-1,1):
        for y in (.198,.806):
            board('Exposed tenon',(side*1.798,y,-1.33),(.005,.058,.041),.001)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in cases:ob.select_set(True)
    bpy.context.view_layer.objects.active=lid
    bpy.ops.object.join()
    lid.name='Chamber cabinet'


def bearer_pegs(layout):
    bars=[dict(s,id=k) for k,s in layout['strings'].items() if s['mid']=='bars']
    plan=bar_frame_plan(bars)
    board=plan['board']
    dx=board['x'][1]-board['x'][0]
    dz=board['z'][1]-board['z'][0]
    outward=np.array([-dz,0.,dx])/math.hypot(dx,dz)
    from pillar_players import Casting
    plugs=Casting()
    for end in plan['ends']:
        for dy in (-.027,.030):
            x=end['x']
            c=np.array([x,board['y']+dy,board_z(plan,x)])+outward*BOARD['half_z']
            plugs.lathe(c,outward,[(-.010,.013),(.0012,.013),(.0017,.011)],'Spruce soundboard',20)
    plugs.object('Marimba drawbore pegs')


def coordinates(obj):
    mesh=obj.data
    slots={i for i,m in enumerate(mesh.materials) if m and m.name in TIMBER}
    if not slots:return
    # A material may cover an entire joined trestle. Find the boards before
    # choosing axes, so both raking legs, the stretcher and end rail retain
    # their own saw direction. Local distances stay in metres along all axes.
    n=len(mesh.vertices)
    xyz=np.empty(n*3,dtype=np.float32)
    mesh.vertices.foreach_get('co',xyz)
    xyz=xyz.reshape(-1,3)
    parent=np.arange(n)
    def root(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]]
            i=parent[i]
        return i
    for e in mesh.edges:
        a,b=e.vertices
        a,b=root(a),root(b)
        if a!=b:parent[b]=a
    groups={}
    for f in mesh.polygons:
        if f.material_index in slots:
            groups.setdefault(root(f.vertices[0]),[]).extend(f.loop_indices)
    if not mesh.uv_layers:mesh.uv_layers.new(name='Long grain')
    if len(mesh.uv_layers)<2:mesh.uv_layers.new(name='Cross section')
    color=mesh.color_attributes.get('Board coordinates')
    if color is None:color=mesh.color_attributes.new('Board coordinates','FLOAT_COLOR','CORNER')
    mesh.color_attributes.active_color=color
    first,second=mesh.uv_layers[0],mesh.uv_layers[1]
    for j,loops in enumerate(groups.values()):
        vi=np.array([mesh.loops[k].vertex_index for k in loops])
        inds,rev=np.unique(vi,return_inverse=True)
        points=xyz[inds].astype('float64')
        points-=points.mean(axis=0)
        _,v=np.linalg.eigh(points.T@points)
        axes=v[:,::-1].copy()
        for k in range(3):
            if axes[np.argmax(abs(axes[:,k])),k]<0:axes[:,k]*=-1.
        coords=points@axes
        span=np.maximum(np.ptp(coords,axis=0),1e-5)
        normal=(coords-coords.min(axis=0))/span
        seed=zlib.crc32((obj.name+'/'+str(j)).encode())/2**32
        for k,index in zip(loops,rev):
            u,v,w=coords[index]
            first.data[k].uv=(u,v)
            second.data[k].uv=(w,seed)
            color.data[k].color=(*normal[index],1.)
    mesh.update()


def build(layout):
    cabinet()
    bearer_pegs(layout)
    for obj in bpy.data.objects:
        if obj.type=='MESH':coordinates(obj)
