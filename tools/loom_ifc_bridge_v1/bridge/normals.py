"""Crease smoothing restricted to connected edge fans, never position-only neighbours."""
import math
import numpy as np

def split_normals(V,F,degrees=60):
 fn=np.cross(V[F[:,1]]-V[F[:,0]],V[F[:,2]]-V[F[:,0]]);length=np.linalg.norm(fn,axis=1);unit=fn/np.maximum(length[:,None],1e-20);threshold=math.cos(math.radians(degrees));incident=[[] for _ in V]
 for i,face in enumerate(F):
  for v in face:incident[v].append(i)
 positions=[];normals=[];out=np.empty_like(F)
 for v,faces in enumerate(incident):
  remaining=set(faces)
  while remaining:
   group={min(remaining)};stack=list(group);remaining-=group
   while stack:
    a=stack.pop()
    for b in sorted(remaining):
     if len(set(F[a])&set(F[b]))>=2 and float(unit[a]@unit[b])>=threshold:group.add(b);stack.append(b);remaining.remove(b)
   n=fn[sorted(group)].sum(0);n/=max(np.linalg.norm(n),1e-20);new=len(positions);positions.append(V[v]);normals.append(n)
   for face in group:out[face,np.where(F[face]==v)[0]]=new
 return np.asarray(positions),out,np.asarray(normals)
