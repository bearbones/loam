"""Contour-corresponding swept joints, with shared topology instead of end caps.

Member centre-lines meet at logical junctions. Trim back both members and fit
cubic tangent transitions. Each indexed profile contour then continues through
that transition. Section dimensions use a periodic C2 field over the whole loop.
"""
import numpy as np
from scipy.interpolate import CubicSpline

def smoothstep(t):
    t=np.clip(t,0,1)
    return t*t*t*(10+t*(-15+6*t))

def rounded_loop(members, trims, spacing=.012):
    """Return centre-line and member labels; trims are distances at each start.

    members[i][-1] must meet members[i+1][0]. A tangent patch replaces the
    trimmed corner. Points at a join belong to one shared ring, never two caps.
    """
    curves=[]; lengths=[]
    for i,points in enumerate(members):
        p=np.asarray(points,float)
        if np.linalg.norm(p[-1]-members[(i+1)%len(members)][0])>1e-6:
            raise ValueError('Members must meet at the logical junction')
        s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
        curves.append(CubicSpline(s,p)); lengths.append(s[-1])
    chunks=[]; labels=[]; joins=[]
    for i,c in enumerate(curves):
        lo=trims[i];hi=lengths[i]-trims[(i+1)%len(curves)]
        if hi<=lo: raise ValueError('Joint trim consumes a member')
        t=np.linspace(lo,hi,max(4,int((hi-lo)/spacing)),endpoint=False)
        chunks.append(c(t)); labels.extend([i]*len(t))
        p0=c(hi);t0=c(hi,1);t0/=np.linalg.norm(t0)
        nxt=(i+1)%len(curves);p1=curves[nxt](trims[nxt]);t1=curves[nxt](trims[nxt],1);t1/=np.linalg.norm(t1)
        chord=np.linalg.norm(p1-p0);angle=np.arccos(np.clip(t0@t1,-1,1))
        handle=chord/3 if angle<1e-5 else chord*(2/3)*np.tan(angle/4)/np.sin(angle/2)
        b1=p0+t0*handle;b2=p1-t1*handle
        u=np.linspace(0,1,max(16,int(2*chord/spacing)),endpoint=False)[:,None]
        patch=(1-u)**3*p0+3*(1-u)**2*u*b1+3*(1-u)*u*u*b2+u**3*p1
        start=sum(len(a) for a in chunks)
        joins.append(dict(from_member=i,to_member=nxt,start=start,count=len(patch),
                          tangent_start=t0.tolist(),tangent_end=t1.tolist(),handle=float(handle)))
        chunks.append(patch);labels.extend([i+.5]*len(patch))
    return np.concatenate(chunks),np.array(labels),joins

def section_field(path,controls):
    """Periodic C2 dimensions from (nearest world point, width, depth) controls."""
    arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
    perimeter=arc[-1]+np.linalg.norm(path[0]-path[-1])
    indices=[int(np.argmin(np.linalg.norm(path-np.array(p),axis=1))) for p,_,_ in controls]
    order=np.argsort(indices); indices=np.array(indices)[order]
    values=np.array([[w,d] for _,w,d in controls])[order]
    if len(np.unique(indices))!=len(indices): raise ValueError('Section controls coincide')
    x=arc[indices];x=np.r_[x,x[0]+perimeter];values=np.vstack([values,values[0]])
    wrapped=(arc-x[0])%perimeter+x[0]
    interval=np.clip(np.searchsorted(x,wrapped,side='right')-1,0,len(x)-2)
    blend=smoothstep((wrapped-x[interval])/(x[interval+1]-x[interval]))
    result=values[interval]*(1-blend[:,None])+values[interval+1]*blend[:,None]
    if result.min()<=0: raise ValueError('Nonpositive section control')
    return result[:,0],result[:,1]
