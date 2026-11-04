from pathlib import Path
import sys,copy,json
import numpy as np
from lxml import etree as E
R=Path(__file__).resolve().parent;sys.path[:0]=[str(R),str(R/'witnesses')]
from bridge.contracts import need,Rejected,finite_vector,revision_transition,binding,resource_path
from bridge.normals import split_normals
from geometry import verify
text=(R/'fixtures/model.ifc').read_text();xml=(R/'fixtures/scene.x3d').read_bytes();positive=verify(text,xml);caught=[]
def reject(name,call):
 try:call()
 except (Rejected,ValueError,KeyError,IndexError) as e:caught.append({'case':name,'code':getattr(e,'code',type(e).__name__)})
 else:raise RuntimeError('SURVIVING_CONTROL: '+name)
for name,mutate in [
 ('ancestor transform',lambda t:t.find(".//Transform[@DEF='IFC_ZUP_TO_YUP']").set('translation','.05 0 0')),
 ('rotation pivot',lambda t:t.find(".//Transform[@DEF='IFC_ZUP_TO_YUP']").set('center','0 .05 0')),
 ('metadata attachment',lambda t:t.find('.//MetadataSet').attrib.pop('containerField')),
 ('winding',lambda t:t.find('.//IndexedTriangleSet').set('index',' '.join(map(str,np.fromstring(t.find('.//IndexedTriangleSet').get('index'),sep=' ',dtype=int).reshape(-1,3)[:,::-1].ravel()))))]:
 t=E.fromstring(xml);mutate(t);reject(name,lambda t=t:verify(text,E.tostring(t)))
for v in [[True,0,0],[float('nan'),0,0],[3,0,0]]:reject('finite bounded vector',lambda v=v:finite_vector(v,3,2))
reject('revision gap',lambda:revision_transition(2,1,3));reject('stale lighting',lambda:binding('a',{'source_sha256':'a','shadow_sha256':'b'},'c'));reject('path escape',lambda:resource_path(R,'../escape'));reject('remote resource',lambda:resource_path(R,'https://example.com/mesh.x3d'))
v=np.array([[0.,0,0],[1,0,0],[0,1,0],[-1,0,0],[0,-1,.2]]);f=np.array([[0,1,2],[0,3,4]]);_,faces,_=split_normals(v,f,85);need(faces[0,0]!=faces[1,0],'DISCONNECTED_NORMAL_FANS')
print(json.dumps({'status':'pass','optimized':not __debug__,'geometry':positive,'negative_controls':caught,'topology_control':'disconnected fans stay separate'}))
