"""Limited planar Euler–Bernoulli frame model: axial extension AND bending.
3 DOFs/node (ux, uy, rotation). Small-displacement linear elasticity only.
A transparent benchmark kernel, not a general FE package. Independent checks
live in tools/test_formlab.py (cantilever axial/bending closed forms).
"""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

def solve(nodes,edges,loads,fixed,E,width,depth):
    nodes=np.asarray(nodes,float); edges=np.asarray(edges,int); loads=np.asarray(loads,float)
    depths=np.broadcast_to(depth,(len(edges),))
    rows=[]; cols=[]; data=[]; locals_=[]; lengths=[]
    for (a,b),h in zip(edges,depths):
        delta=nodes[b]-nodes[a]; L=np.linalg.norm(delta); c,s=delta/L
        if L<=0 or h<=0 or width<=0 or E<=0: raise ValueError('Positive lengths, sections and stiffness required')
        A=width*h; I=width*h**3/12; axial=E*A/L; bend=E*I
        k=np.array([[axial,0,0,-axial,0,0],
           [0,12*bend/L**3,6*bend/L**2,0,-12*bend/L**3,6*bend/L**2],
           [0,6*bend/L**2,4*bend/L,0,-6*bend/L**2,2*bend/L],
           [-axial,0,0,axial,0,0],
           [0,-12*bend/L**3,-6*bend/L**2,0,12*bend/L**3,-6*bend/L**2],
           [0,6*bend/L**2,2*bend/L,0,-6*bend/L**2,4*bend/L]])
        r=np.array([[c,s,0],[-s,c,0],[0,0,1.]])
        T=np.zeros((6,6)); T[:3,:3]=r; T[3:,3:]=r
        dof=np.r_[np.arange(a*3,a*3+3),np.arange(b*3,b*3+3)]
        g=T.T@k@T
        rows.extend(np.repeat(dof,6));cols.extend(np.tile(dof,6));data.extend(g.ravel())
        locals_.append((dof,T,k)); lengths.append(L)
    nd=len(nodes)*3; K=coo_matrix((data,(rows,cols)),shape=(nd,nd)).tocsr()
    free=np.setdiff1d(np.arange(nd),fixed); F=loads.reshape(nd); u=np.zeros(nd)
    u[free]=spsolve(K[free][:,free],F[free])
    if not np.isfinite(u).all(): raise ValueError('Unrestrained or singular frame')
    residual=K@u-F; forces=np.array([k@T@u[dof] for dof,T,k in locals_])
    return dict(displacement=u.reshape(-1,3),compliance=float(F@u),
                residual=float(np.linalg.norm(residual[free])/max(np.linalg.norm(F),1e-12)),
                reactions=residual.reshape(-1,3),end_forces=forces,
                volume=float(np.asarray(lengths)@(width*depths)),lengths=np.array(lengths))
