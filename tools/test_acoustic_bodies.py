"""Inspect the playing surfaces and acoustic cavities of the two shipped GLBs."""
import json
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from formlab.layout import BAR, bar_frame_plan
from formlab.recipes import soundboard


class Model:
    def __init__(self, path):
        with path.open('rb') as f:
            f.seek(12)
            length, _ = struct.unpack('<II', f.read(8))
            self.doc = json.loads(f.read(length))
            f.read(8)
            self.buffer = f.read()
        self.nodes = {n['name']: n for n in self.doc['nodes']}

    def array(self, i):
        accessor = self.doc['accessors'][i]
        view = self.doc['bufferViews'][accessor['bufferView']]
        dims = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[accessor['type']]
        dtype = np.dtype({5121: 'u1', 5123: '<u2', 5125: '<u4', 5126: '<f4'}[accessor['componentType']])
        return np.ndarray((accessor['count'], dims), dtype, self.buffer,
                          offset=view.get('byteOffset', 0)+accessor.get('byteOffset', 0),
                          strides=(view.get('byteStride', dims*dtype.itemsize),dtype.itemsize))

    def surfaces(self, name):
        return self.doc['meshes'][self.nodes[name]['mesh']]['primitives']

    def triangles(self, name):
        # The bodies probed here are authored in world coordinates.
        node = self.nodes[name]
        assert not any(k in node for k in ('matrix','rotation','translation','scale')), name
        return np.concatenate([self.array(p['attributes']['POSITION'])[self.array(p['indices']).reshape(-1,3)]
                               for p in self.surfaces(name)])


def first_hit(tris, start, direction):
    """Distance to the first front or back face. Infinity means a through hole."""
    d = np.array(direction, dtype=float)
    d /= np.linalg.norm(d)
    a, b, c = tris.transpose(1,0,2)
    u, v = b-a, c-a
    p = np.cross(d,v)
    det = np.sum(u*p,axis=1)
    inv = np.divide(1.,det,out=np.zeros_like(det),where=np.abs(det)>1e-10)
    t = np.asarray(start)-a
    s = np.sum(t*p,axis=1)*inv
    q = np.cross(t,u)
    h = (q@d)*inv
    distance = np.sum(v*q,axis=1)*inv
    valid = (np.abs(det)>1e-10)&(s>=-1e-6)&(h>=-1e-6)&(s+h<=1.+1e-6)&(distance>1e-5)
    return float(distance[valid].min(initial=np.inf))


def inspect(name):
    model = Model(ROOT/'harness/assets'/f'{name}.glb')
    layout = json.loads((ROOT/'harness/assets'/f'{name}.json').read_text())
    elements = [dict(s,id=sid) for sid,s in layout['strings'].items()]
    bars = [s for s in elements if s['mid']=='bars']
    frame = bar_frame_plan(bars)
    for i,el in enumerate(bars):
        sid = el['id']
        t = model.triangles(sid+' bar')
        a,b = np.array(el['a']),np.array(el['b'])
        p = (a+b)/2
        origin = p-[0,.2,0]
        centre = first_hit(t,origin,[0,1,0])
        end = first_hit(t,origin+.44*(b-a),[0,1,0])
        assert .035 < centre-end < BAR['thick'], (sid,'undercut',centre,end)
        for posts in frame['posts'].values():
            l,r = posts[i:i+2]
            start = np.array([l['x'],frame['cord_y'],l['z']])
            d = np.array([r['x'],frame['cord_y'],r['z']])-start
            assert not np.isfinite(first_hit(t,start,d)), (sid,'blocked suspension bore')
            assert first_hit(t,start+[0,.019,0],d)<np.linalg.norm(d), (sid,'missing bore wall')
        tube = model.triangles(sid+' resonator')
        rr = frame['resonators'][i]
        mouth = [rr['x'],rr['top']-.04,rr['z']]
        assert not np.isfinite(first_hit(tube,mouth,[0,1,0])), (sid,'sealed resonator')
        assert 0 < first_hit(tube,mouth,[1,0,0]) < rr['radius'], (sid,'missing tube wall')
    for el in elements:
        a,b = np.array(el['a']),np.array(el['b'])
        x,y,z = (a+b)/2
        sid = el['id']
        if el['mid']=='blocks':
            t = model.triangles(sid+' bar')
            length=abs(b[2]-a[2])
            origin = [x,y-.038,z+length/2+.02]
            depth=first_hit(t,origin,[0,0,-1])
            assert .55*length<depth<length, (sid,'sound chamber depth',depth)
            assert first_hit(t,[x,y+.10,z],[0,-1,0])<.101, (sid,'missing tongue')
        elif el['mid']=='bells':
            t = model.triangles(sid+' bell')
            hit=first_hit(t,[x,y+.08,z],[0,-1,0])
            assert abs(hit-.08)<.001, (sid,'hammer misses glass shoulder',hit)
        if el['struck']:
            part=sid+(' bell' if el['mid']=='bells' else ' bar')
            p,=model.surfaces(part)
            assert 'targets' in p and 'TEXCOORD_0' in p['attributes'], part
    for mid in ('rake','harp'):
        board=soundboard([s for s in elements if s['mid']==mid])[0]
        rings=board.vertices[:-2].reshape(-1,8,3)
        rings=rings[np.linspace(0,len(rings)-1,49,dtype=int)]
        shell=model.triangles(mid+' staved soundbox')
        for frac in (.25,.53,.79):
            row=rings[round(frac*(len(rings)-1))]
            p=row.mean(axis=0)+[0,0,.3]
            assert not np.isfinite(first_hit(shell,p,[0,0,-1])), (mid,'blocked port')
            assert first_hit(shell,p+.34*(row[3]-row[0]),[0,0,-1])<.3, (mid,'missing back')
    assert first_hit(model.triangles('Chamber cabinet'),[0,.54,-1.12],[0,0,-1])>.6
    # Grain travels one metre per model metre on each cut face. Measure it on
    # triangle edges, where a normalized or stretched UV island is detectable.
    wood={'Rosewood','Oiled walnut','Spruce soundboard','Spruce interior'}
    for mesh in model.doc['meshes']:
        for prim in mesh['primitives']:
            if model.doc['materials'][prim['material']]['name'] not in wood: continue
            a=prim['attributes']
            assert {'TEXCOORD_0','TEXCOORD_1','COLOR_0'}<=a.keys(),mesh['name']
            coords=np.column_stack((model.array(a['TEXCOORD_0']),model.array(a['TEXCOORD_1'])[:,0]))
            v=model.array(a['POSITION'])
            tri=model.array(prim['indices']).reshape(-1,3)[::19,:2]
            def distances(points):
                return np.linalg.norm(points[tri[:,0]]-points[tri[:,1]],axis=1)
            assert np.max(abs(distances(v)-distances(coords)))<.0001,mesh['name']
    lid=model.triangles('Chamber cabinet')
    assert first_hit(lid,[-1.70,.94,-1.455],[0,-1,0])>.033
    for x in (-1.58,-1.23):
        assert abs(first_hit(lid,[x,.94,-1.455],[0,-1,0])-.0246)<.001
    for aid,cfg in layout['arms'].items():
        if cfg['kind']=='mallet' and cfg.get('hands',0)>=2:
            for part in ('tool','mallet2_head'):
                vertices=np.concatenate([model.array(p['attributes']['POSITION']) for p in model.surfaces(aid+'__'+part)])
                centre=.5*(vertices.max(axis=0)+vertices.min(axis=0))
                radius=np.linalg.norm(vertices-centre,axis=1).max()
                assert .059<radius<=.062,(aid,part,'felt clearance sphere',radius)
        if cfg['kind'] not in ('pick','rake'): continue
        if 'pillar_player' in cfg:
            mount=cfg['pillar_player']
            assert aid+'__carriage' not in model.nodes
            assert aid+' pillar saddle' in model.nodes
            assert np.allclose(model.nodes[aid+'__upper_stock']['translation'],mount['shoulder'])
            for d in ('thumb','d2','d3','d4'):
                base=aid+'__digit_'+d
                names=[aid+'__palm',base,base+'_middle',base+'_distal',aid+'__pad_'+d]
                for parent,child in zip(names,names[1:]):
                    assert any(model.doc['nodes'][i] is model.nodes[child] for i in model.nodes[parent]['children'])
                tip=model.nodes[names[-1]]['translation']
                cap=next(p for p in model.surfaces(names[-2]) if model.doc['materials'][p['material']]['name']=='Pressed horn')
                radii=np.linalg.norm(model.array(cap['attributes']['POSITION'])-tip,axis=1)
                assert np.count_nonzero(np.isclose(radii,mount['pad_radius'],atol=1e-5))>=30
            continue
        stud=aid+' palm stud'
        shank=aid+'__shank'
        assert any(model.doc['nodes'][i] is model.nodes[stud] for i in model.nodes[shank]['children'])
        pivot=np.array(model.nodes[stud]['translation'])
        assert np.allclose(pivot,cfg['drives']['wrist_flex']['mount_offset'],atol=1e-5)
        def height_range(name):
            v=np.concatenate([model.array(p['attributes']['POSITION']) for p in model.surfaces(name)])
            return v[:,1].min(),v[:,1].max()
        lo,hi=height_range(stud)
        assert lo+pivot[1]<height_range(shank)[1]-.005 and hi>.009,(aid,'detached wrist stud')
        for d in ('thumb','d2','d3','d4'):
            mesh_name=aid+'__digit_'+d
            pad=aid+'__pad_'+d
            marker=model.nodes[pad]
            node=model.nodes[mesh_name]
            def child(parent,part):
                assert any(model.doc['nodes'][i] is part for i in parent['children']), pad
            middle=model.nodes[mesh_name+'_middle']
            distal=model.nodes[mesh_name+'_distal']
            child(model.nodes[aid+'__tool'],node)
            child(node,middle)
            child(middle,distal)
            child(distal,marker)
            assert np.allclose(node['translation'],cfg['hand']['knuckles'][d],atol=1e-5)
            point=marker.get('translation',[0.,0.,0.])
            horn=next(p for p in model.surfaces(mesh_name+'_distal') if 'horn' in model.doc['materials'][p['material']]['name'].lower())
            error=np.linalg.norm(model.array(horn['attributes']['POSITION'])-point,axis=1).min()
            assert error<.00012, (pad,'contact marker off horn',error)
    print(name,'acoustic cavities, speaking surfaces and fingertip meshes PASS')


if __name__=='__main__':
    for asset in ('clockwork','clockwork_expanded'):
        inspect(asset)
