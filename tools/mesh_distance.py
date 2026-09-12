"""BVH distance with oriented ray crossings for closed, outward-wound parts.

Nearest triangle normals do not classify concave corners reliably. Oriented
crossings also retain occupied overlaps of separately closed joinery pieces.
"""
from mathutils import Vector
from mathutils.bvhtree import BVHTree

class ClosedSurface:
    def __init__(self,vertices,faces):
        self.tree=BVHTree.FromPolygons([Vector(v) for v in vertices],faces,all_triangles=True)
        self.low=Vector([min(v[i] for v in vertices) for i in range(3)])
        self.high=Vector([max(v[i] for v in vertices) for i in range(3)])
    def signed_distance(self,p):
        _,_,_,distance=self.tree.find_nearest(p)
        if distance<1e-7 or any(p[i]<self.low[i] or p[i]>self.high[i] for i in range(3)):
            return distance
        inside=[]
        for direction in (Vector((.371,.529,.763)).normalized(),Vector((-.643,.719,.263)).normalized(),Vector((.213,-.419,.881)).normalized()):
            origin=p.copy(); winding=0
            for _ in range(512):
                point,normal,_,_=self.tree.ray_cast(origin,direction)
                if point is None: break
                winding+=1 if normal.dot(direction)>0 else -1
                origin=point+direction*1e-6
            else: raise RuntimeError('Ray crossing limit exceeded')
            inside.append(winding!=0)
        return -distance if sum(inside)>=2 else distance
