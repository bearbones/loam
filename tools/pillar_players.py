"""Pillar saddle, two pinned arm links and a harp hand with string-parallel axles.
All authored coordinates are Godot metres. Moving parts have rigid local frames.
"""
import math
import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from acoustic_bodies import vec

BRASS='Satin brass'
STEEL='Blued steel'
BRONZE='Phosphor bronze'
WOOD='Oiled walnut'
HORN='Pressed horn'
UP=np.array([0.,1.,0.])
X=np.array([1.,0.,0.])
Z=np.array([0.,0.,1.])


class Casting:
    def __init__(self):
        self.points=[]
        self.faces=[]
        self.materials=[]
        self.slots=[]

    def loft(self, rows, material):
        base=len(self.points)
        n=len(rows[0])
        self.points.extend(p for row in rows for p in row)
        faces=[tuple(base+i for i in reversed(range(n)))]
        for j in range(len(rows)-1):
            k=base+j*n
            faces.extend((k+i,k+(i+1)%n,k+n+(i+1)%n,k+n+i) for i in range(n))
        faces.append(tuple(base+(len(rows)-1)*n+i for i in range(n)))
        self.faces.extend(faces)
        if material not in self.materials:self.materials.append(material)
        self.slots.extend([self.materials.index(material)]*len(faces))

    def lathe(self,origin,axis,profile,material,n=24):
        axis=np.asarray(axis,dtype=float)
        axis=axis/np.linalg.norm(axis)
        u=np.cross(axis,UP if abs(axis[1])<.85 else Z)
        u/=np.linalg.norm(u)
        v=np.cross(axis,u)
        ring=[math.cos(a)*u+math.sin(a)*v for a in np.arange(n)*math.tau/n]
        self.loft([[origin+axis*h+r*p for p in ring] for h,r in profile],material)

    def ball(self,c,r,material):
        self.lathe(c,UP,[(r*math.sin(a),r*math.cos(a)) for a in np.linspace(-1.565,1.565,17)],material,32)

    def object(self,name,parent=None,position=(0,0,0)):
        data=bpy.data.meshes.new(name)
        data.from_pydata([vec(p) for p in self.points],[],self.faces)
        data.update()
        for m in self.materials:data.materials.append(bpy.data.materials[m])
        for poly,slot in zip(data.polygons,self.slots):
            poly.material_index=slot
            poly.use_smooth=len(poly.vertices)==4
        bm=bmesh.new()
        bm.from_mesh(data)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        bm.to_mesh(data)
        bm.free()
        obj=bpy.data.objects.new(name,data)
        bpy.context.collection.objects.link(obj)
        obj.parent=parent
        obj.location=vec(position)
        return obj


def spindle(part,centre,axis,r,length):
    part.lathe(centre,axis,[(-length*.52,r*.68),(-length*.49,r),(-length*.43,r),
                           (-length*.40,r*.65),(length*.40,r*.65),
                           (length*.43,r),(length*.49,r),(length*.52,r*.68)],STEEL)


def arm_link(aid,name,length,r):
    p=Casting()
    for fraction in (0.,1.):
        c=UP*(length*fraction)
        p.ball(c,r*1.04,BRONZE)
        spindle(p,c,X,r*.67,r*2.64)
    # A slightly cambered walnut stock narrows toward its distal brass ferrule.
    angles=np.arange(32)*math.tau/32
    rows=[]
    for u,w in [(0.027,.67),(.065,1.05),(.14,1.18),(.32,1.21),(.62,.99),(.87,.79),(.966,.62)]:
        rows.append([(r*w*math.cos(a),u*length,r*(.32*math.sin(math.pi*u)+w*.82*math.sin(a))) for a in angles])
    p.loft(rows,WOOD)
    for u,w in [(.055,1.09),(.89,.85)]:
        p.lathe(UP*(u*length),UP,[(-.013,r*w*.93),(-.011,r*w),(.010,r*w),(.013,r*w*.94)],BRASS)
    # Steel tie rod beneath the stock is pinned between the end shoes.
    start=np.array([0.,.04,-r*.75]);end=np.array([0.,length-.035,-r*.73])
    p.lathe(start,end-start,[(0.,.006),(.013,.009),(.020,.006),(np.linalg.norm(end-start),.006)],STEEL,16)
    return p.object(aid+'__'+name)


def saddle(aid,centre,shoulder):
    frame=bpy.data.objects['form_harp_carved']
    tree=BVHTree.FromObject(frame,bpy.context.evaluated_depsgraph_get())
    p=Casting()
    for side in (-1,1):
        # Cast to the actual carved pillar. The shoes bed into its moulding;
        # the outer surface stands clear of the stone at both split lines.
        rows=[]
        for a in np.linspace(.038,math.pi-.038,41)+(0 if side==1 else math.pi):
            ray=np.array([math.cos(a),0.,math.sin(a)])
            row=[]
            for dh,lip in [(-.060,-.006),(-.060,.016),(-.051,.026),(.051,.026),(.060,.016),(.060,-.006)]:
                c=centre+UP*dh
                hit,_,_,_=tree.ray_cast(vec(c+.55*ray),vec(-ray),.55)
                radius=.145 if hit is None else (hit-vec(c)).length
                row.append(c+(radius+lip)*ray)
            rows.append(row)
        p.loft(rows,BRONZE)
    axis=np.array([0.,0.,np.sign(shoulder[2]-centre[2])])
    depth=abs(shoulder[2]-centre[2])
    p.lathe(centre,axis,[(.105,.078),(.178,.083),(.20,.068),(depth-.06,.053),(depth-.028,.067),(depth,.058)],BRASS,36)
    p.ball(shoulder,.073,STEEL)
    for dx in (-.066,.066):
        for dy in (-.037,.037):
            p.lathe(centre+[dx,dy,0],axis,[(.135,.010),(.19,.010),(.191,.016),(.203,.016)],STEEL,6)
    return p.object(aid+' pillar saddle')


def hand(aid):
    palm=Casting()
    palm.ball([0.,0.,-.063],.030,BRONZE)
    # Brass chassis with a worn walnut palm scale, widening from the carpal
    # bearing toward the finger row. The open thumb web clears its first pin.
    angles=np.arange(36)*math.tau/36
    for side,material in [(-1,BRASS),(1,WOOD)]:
        rows=[]
        for z,x,w,h in [(-.070,0,.010,.017),(-.059,.001,.017,.027),
                         (-.040,.002,.023,.041),(-.019,.002,.024,.050),
                         (-.003,0,.021,.051),(.010,-.002,.016,.041),(.017,0,.009,.028)]:
            rows.append([(x+side*.007+w*.62*math.cos(a),h*math.sin(a),z) for a in angles])
        palm.loft(rows,material)
    for y,z in [(-.026,-.021),(.025,-.024)]:
        palm.lathe(np.array([0.,y,z]),X,[(.012,.0038),(.024,.0038),(.0245,.0053),(.0256,.0053)],BRASS,16)
    # A fan of metacarpals carries the knuckle pins from the wrist bearing.
    ys=(.055,.019,-.017,-.052)
    sockets=[np.array([x,y,z]) for x,y,z in zip((-.007,.002,.003,-.003),ys,(.012,.030,.027,.012))]
    for k in sockets:
        a=np.array([0.,k[1]*.24,-.060]);delta=k-a
        palm.lathe(a,delta,[(0.,.012),(.009,.015),(.70*np.linalg.norm(delta),.011),(np.linalg.norm(delta),.012)],BRASS)
        spindle(palm,k,UP,.0075,.027)
    wrist=palm.object(aid+'__palm')
    for d,k,f in zip(('thumb','d2','d3','d4'),sockets,(.86,1.,.95,.83)):
        parent=wrist
        positions=[k,Z*.069*f,Z*.047*f]
        for index,(suffix,L) in enumerate(zip(('','_middle','_distal'),(.069*f,.047*f,.042*f))):
            part=Casting()
            part.lathe(np.zeros(3),UP,[(-.009,.010),(-.007,.013),(.007,.013),(.009,.010)],BRONZE)
            spindle(part,np.zeros(3),UP,.0058,.025)
            part.lathe(np.zeros(3),Z,[(.004,.009),(.012,.010),(L*.66,.0065),(L-.004,.006)],BRASS)
            if index<2:
                # The outgoing finger actually straddles the following hinge.
                # Flattened side straps meet the axle at the next knuckle.
                for cheek in (-1.,1.):
                    rows=[]
                    for z,w in [(.002,.0062),(L*.28,.0094),(L*.65,.0068),(L-.002,.009),(L+.004,.006)]:
                        rows.append([(w*math.cos(a),cheek*.009+.0022*math.sin(a),z) for a in angles[::2]])
                    part.loft(rows,BRONZE)
            if index==2:
                part.lathe(np.zeros(3),Z,[(L*.40,.007),(L*.49,.009),(L*.66,.009),(L*.69,.007)],BRONZE)
                part.lathe(np.zeros(3),Z,[(L*.65,.0079),(L*.82,.0083),(L,.0075)],HORN)
                part.ball(Z*L,.0075,HORN)
            parent=part.object(aid+'__digit_'+d+suffix,parent,positions[index])
        marker=bpy.data.objects.new(aid+'__pad_'+d,None)
        bpy.context.collection.objects.link(marker);marker.parent=parent
        marker.location=vec(Z*(.042*f));marker.empty_display_size=.003
    return wrist


def aim(obj,a,b,axis):
    y=Vector(b-a).normalized()
    x=Vector(axis);x=(x-y*y.dot(x)).normalized()
    basis=Matrix([vec(x),-vec(x.cross(y)),vec(y)]).transposed()
    obj.matrix_world=Matrix.Translation(vec(a))@basis.to_4x4()


def build(layout):
    wires=[v for v in layout['strings'].values() if v['mid']=='harp']
    left=min(v['a'][0] for v in wires)
    z=wires[0]['a'][2]
    for aid,cfg in layout['arms'].items():
        if cfg['mid']!='harp':continue
        for ob in list(bpy.data.objects):
            if ob.name.startswith((aid+'__',aid+' ', 'form_'+aid+'_')):
                bpy.data.objects.remove(ob,do_unlink=True)
        i=cfg['index'];side=(-1.,1.,-1.)[i]
        centre=np.array([left-.46,(1.39,2.03,2.68)[i],z+.20])
        root=centre+Z*(side*(.56 if side<0 else .38))
        l1,l2=((.60,.56),(.91,.87),(1.17,1.14))[i]
        rest=np.array([(-.74,-.16,.56)[i],(1.20,1.72,2.28)[i],z+side*.26])
        pole=np.array([-.14,(-.28,.33,.12)[i],side])
        cfg['pillar_player']=dict(shoulder=root.tolist(),upper=l1,forearm=l2,side=side,
                                  park=rest.tolist(),pole=pole.tolist(),pad_radius=.0075)
        saddle(aid,centre,root)
        upper=arm_link(aid,'upper_stock',l1,.048);lower=arm_link(aid,'forearm_stock',l2,.038)
        palm=hand(aid)
        # At rest the pad chains point into the string plane, thumb uppermost.
        palm.location=vec(rest)
        palm.rotation_euler.z=math.pi if side>0 else 0.
        w=rest+side*Z*.063;d=w-root;dist=np.linalg.norm(d);unit=d/dist
        bend=pole-unit*np.dot(pole,unit);bend/=np.linalg.norm(bend)
        along=(l1*l1-l2*l2+dist*dist)/(2*dist)
        elbow=root+unit*along+bend*math.sqrt(max(0.,l1*l1-along*along))
        axle=np.cross(unit,bend);aim(upper,root,elbow,axle);aim(lower,elbow,w,axle)
        for ob in palm.children:
            if '__digit_' in ob.name:
                ob.rotation_euler.z=.66
                ob.children[0].rotation_euler.z=1.32
                ob.children[0].children[0].rotation_euler.z=1.40
    layout['form_objects']=[n for n in layout.get('form_objects',[]) if not n.startswith('form_harp_arm')]
