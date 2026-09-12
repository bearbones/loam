"""Thin Blender adapter: union analytic components, finish surfaces and transport grain.
The recipe JSON is produced by formlab without importing bpy.
"""
import bpy,bmesh,json,math
import numpy as np
from mathutils import Vector, kdtree

def convert(p): return (p[0],-p[2],p[1])
def make_form(entry,material):
    vertices=[]; faces=[]; samples=[]; source_uv=[]
    for component in entry['pieces']:
        offset=len(vertices); vertices.extend(convert(p) for p in component['vertices'])
        source_uv.extend(component['uv'])
        faces.extend(tuple(offset+i for i in f) for f in component['faces'])
        path=np.array(component['path']); tangent=np.gradient(path,axis=0); tangent/=np.linalg.norm(tangent,axis=1)[:,None]
        arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
        for p,t,u in zip(path,tangent,arc):
            normal=np.cross([0,0,1],t)
            if np.linalg.norm(normal)<1e-6: normal=np.cross([1,0,0],t)
            normal/=np.linalg.norm(normal); binormal=np.cross(t,normal)
            samples.append((Vector(convert(p)),Vector(convert(t)),Vector(convert(normal)),Vector(convert(binormal)),float(u)))
    data=bpy.data.meshes.new(entry['name']); data.from_pydata(vertices,[],faces); data.update()
    if entry.get('finish')=='profiled':
        uv=data.uv_layers.new(name='Authored sweep grain')
        for loop in data.loops: uv.data[loop.index].uv=source_uv[loop.vertex_index]
    obj=bpy.data.objects.new(entry['name'],data); bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active=obj
    if entry.get('finish')=='profiled':
        bevel=obj.modifiers.new('Small joinery edge breaks','BEVEL'); bevel.width=.003; bevel.segments=2; bevel.limit_method='ANGLE'; bevel.angle_limit=.5
        bpy.ops.object.modifier_apply(modifier=bevel.name)
        # Bevel intersections can leave sub-micron slivers; remove only those
        # before the existing closed-edge/area validation. Preserve the profile.
        if not entry['name'].endswith(('_soundboard','_actionplate')):
            bm=bmesh.new();bm.from_mesh(obj.data)
            bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
            bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-6)
            bm.to_mesh(obj.data);bm.free()
        obj.data.use_auto_smooth=True; obj.data.auto_smooth_angle=.65
    else:
        obj.data.remesh_voxel_size=.014; obj.data.remesh_voxel_adaptivity=0
        bpy.ops.object.voxel_remesh()
        smooth=obj.modifiers.new('Organic junction smoothing','SMOOTH'); smooth.factor=.45; smooth.iterations=3
        bpy.ops.object.modifier_apply(modifier=smooth.name)
        decimate=obj.modifiers.new('Render mesh budget','DECIMATE'); decimate.ratio=.24
        bpy.ops.object.modifier_apply(modifier=decimate.name)
    for polygon in obj.data.polygons: polygon.use_smooth=True
    obj.data.materials.clear(); obj.data.materials.append(material)
    if entry.get('finish')!='profiled':
        tree=kdtree.KDTree(len(samples))
        for i,s in enumerate(samples): tree.insert(s[0],i)
        tree.balance()
        # Grain follows the nearest branch's arc length, rather than a global XYZ axis.
        uv=obj.data.uv_layers.new(name='Growth grain')
        coords=[]
        for vertex in obj.data.vertices:
            _,index,_=tree.find(vertex.co); p,t,n,b,u=samples[index]; delta=vertex.co-p
            coords.append((u+delta.dot(t),math.atan2(delta.dot(b),delta.dot(n))*.12))
        for loop in obj.data.loops: uv.data[loop.index].uv=coords[loop.vertex_index]
    obj['form_classification']=entry['classification']
    obj['form_recipe']='formlab/2'; obj['finish']=entry.get('finish','voxel union')
    obj.data.calc_loop_triangles()
    verts=np.array([[v.co.x,v.co.z,-v.co.y] for v in obj.data.vertices])
    triangles=np.array([list(t.vertices) for t in obj.data.loop_triangles])
    edges=np.sort(np.concatenate([triangles[:,[0,1]],triangles[:,[1,2]],triangles[:,[2,0]]]),axis=1)
    _,counts=np.unique(edges,axis=0,return_counts=True)
    area=np.linalg.norm(np.cross(verts[triangles[:,1]]-verts[triangles[:,0]],verts[triangles[:,2]]-verts[triangles[:,0]]),axis=1)
    # Main frames have shared-ring topology; ferrules remain closed functional parts.
    check=dict(vertices=len(verts),triangles=len(triangles),nonmanifold_edges=int(np.sum(counts!=2)),degenerate_triangles=int(np.sum(area<1e-12)))
    if check['nonmanifold_edges'] or check['degenerate_triangles']: raise ValueError((entry['name'],check))
    print('FORM MESH:',entry['name'],check)
    return obj,dict(name=entry['name'],vertices=verts.tolist(),faces=triangles.tolist(),check=check)
