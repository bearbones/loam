"""Continuous variable-section sweeps, parallel-transport frames, and mesh rulers."""
from dataclasses import dataclass
import numpy as np
from scipy.interpolate import CubicSpline

@dataclass
class Mesh:
    vertices: np.ndarray
    faces: np.ndarray
    uv: np.ndarray
    path: np.ndarray
    widths: np.ndarray
    depths: np.ndarray

    def to_dict(self):
        return {k:getattr(self,k).tolist() for k in self.__dataclass_fields__}

def sample_curve(points, count=128, closed=False):
    p=np.asarray(points,float)
    if closed and np.linalg.norm(p[-1]-p[0])>1e-10: p=np.vstack([p,p[0]])
    distance=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    if np.any(np.diff(distance)<1e-9): raise ValueError('Coincident curve control points')
    curve=CubicSpline(distance,p,bc_type='periodic' if closed else 'natural')
    # Resample by arc length, avoiding dense rings at clustered control points.
    dense=curve(np.linspace(0,distance[-1],count*12))
    arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(dense,axis=0),axis=1))]
    t=np.interp(np.linspace(0,arc[-1],count,endpoint=not closed),arc,np.linspace(0,distance[-1],len(dense)))
    return curve(t)

def transport_frames(path,closed=False):
    p=np.asarray(path,float)
    tangent=np.roll(p,-1,axis=0)-np.roll(p,1,axis=0) if closed else np.gradient(p,axis=0)
    tangent/=np.linalg.norm(tangent,axis=1)[:,None]
    # Use Z as the initial binormal for planar XY structures.
    seed=np.array([0.,0.,1.])
    if abs(seed@tangent[0])>.9: seed=np.array([1.,0.,0.])
    n=np.empty_like(p); n[0]=np.cross(seed,tangent[0]); n[0]/=np.linalg.norm(n[0])
    for i in range(1,len(p)):
        axis=np.cross(tangent[i-1],tangent[i]); length=np.linalg.norm(axis)
        if length<1e-10: n[i]=n[i-1]
        else:
            axis/=length; angle=np.arctan2(length,tangent[i-1]@tangent[i])
            n[i]=n[i-1]*np.cos(angle)+np.cross(axis,n[i-1])*np.sin(angle)+axis*(axis@n[i-1])*(1-np.cos(angle))
        n[i]-=tangent[i]*(tangent[i]@n[i]); n[i]/=np.linalg.norm(n[i])
    # Distribute loop holonomy to avoid a seam on nonplanar closed curves.
    if closed:
        last=n[-1]-tangent[0]*(tangent[0]@n[-1]); last/=np.linalg.norm(last)
        twist=np.arctan2(tangent[0]@np.cross(last,n[0]),last@n[0])
        for i in range(len(p)):
            a=twist*i/len(p); n[i]=n[i]*np.cos(a)+np.cross(tangent[i],n[i])*np.sin(a)
    return tangent,n,np.cross(tangent,n)

def sweep(path,width=.12,depth=.10,sides=24,closed=False,ridge=0.,profile=None):
    p=np.asarray(path,float); count=len(p)
    if count<3 or sides<8: raise ValueError('A sweep needs 3 path samples and 8 profile samples')
    w=np.broadcast_to(width,(count,)).copy(); d=np.broadcast_to(depth,(count,)).copy()
    if min(w.min(),d.min())<=0: raise ValueError('Positive section radii required')
    _,normal,binormal=transport_frames(p,closed)
    if profile is not None:
        profile=np.asarray(profile,float); sides=profile.shape[-2]
        if profile.ndim==3 and len(profile)!=count: raise ValueError('One profile required per ring')
    angle=np.arange(sides)*2*np.pi/sides
    # Lenticular ridges run longitudinally; their scale is a declared design control.
    if profile is None:
        bump=np.exp(-((np.sin(angle)-.72)/.18)**2)*ridge
        profile=np.c_[np.cos(angle),np.sin(angle)+bump]
    profiles=np.broadcast_to(profile,(count,sides,2))
    vertices=(p[:,None,:]+normal[:,None,:]*(w[:,None,None]*profiles[:,:,0,None])+
              binormal[:,None,:]*(d[:,None,None]*profiles[:,:,1,None])).reshape(-1,3)
    arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    uv=np.stack(np.meshgrid(arc,angle/(2*np.pi),indexing='ij'),axis=-1).reshape(-1,2)
    faces=[]
    for i in range(count if closed else count-1):
        j=(i+1)%count
        for k in range(sides):
            q=(k+1)%sides; a=i*sides+k; b=i*sides+q; c=j*sides+q; e=j*sides+k
            faces.extend(((a,b,c),(a,c,e)))
    if not closed:
        for end in (0,count-1):
            centre=len(vertices); vertices=np.vstack([vertices,p[end]]); uv=np.vstack([uv,[arc[end],.5]])
            for k in range(sides):
                q=(k+1)%sides
                faces.append((centre,end*sides+q,end*sides+k) if end==0 else (centre,end*sides+k,end*sides+q))
    faces=np.asarray(faces,int)
    signed=np.einsum('ij,ij->i',vertices[faces[:,0]],np.cross(vertices[faces[:,1]],vertices[faces[:,2]])).sum()/6
    if signed<0: faces=faces[:,::-1].copy()
    return Mesh(vertices,faces,uv,p,w,d)

def validate_mesh(mesh):
    v,f=mesh.vertices,mesh.faces
    twice_area=np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)
    edges=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1)
    _,counts=np.unique(edges,axis=0,return_counts=True)
    signed=np.einsum('ij,ij->i',v[f[:,0]],np.cross(v[f[:,1]],v[f[:,2]])).sum()/6
    result=dict(vertices=len(v),triangles=len(f),boundary_or_nonmanifold_edges=int(np.sum(counts!=2)),
                degenerate_triangles=int(np.sum(twice_area<1e-12)),volume=float(signed),finite=bool(np.isfinite(v).all()))
    result['ok']=bool(result['finite'] and result['boundary_or_nonmanifold_edges']==0 and result['degenerate_triangles']==0 and signed>0)
    return result
