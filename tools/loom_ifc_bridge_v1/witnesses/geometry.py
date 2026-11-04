"""Independent world-triangle witness: geometry is re-read from IFC, not trusted from the index."""
from pathlib import Path
import json,sys,collections,math
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching
from lxml import etree as E
import ifcopenshell,ifcopenshell.geom,ifcopenshell.guid
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bridge.contracts import need
R=Path(__file__).resolve().parents[1]

def matrix(node):
 m=np.eye(4)
 if node.tag!='Transform':return m
 def vector(name,default,n):
  v=np.fromstring(node.get(name,default),sep=' ');need(len(v)==n and np.isfinite(v).all(),'TRANSFORM_FINITE');return v
 def rotation(a):
  length=np.linalg.norm(a[:3]);need(length>0,'ROTATION_AXIS');x,y,z=a[:3]/length;c=math.cos(a[3]);q=math.sin(a[3]);v=1-c
  return np.array([[x*x*v+c,x*y*v-z*q,x*z*v+y*q],[y*x*v+z*q,y*y*v+c,y*z*v-x*q],[z*x*v-y*q,z*y*v+x*q,z*z*v+c]])
 t=vector('translation','0 0 0',3);c=vector('center','0 0 0',3);s=vector('scale','1 1 1',3);r=rotation(vector('rotation','0 0 1 0',4));sr=rotation(vector('scaleOrientation','0 0 1 0',4))
 m[:3,:3]=r@sr@np.diag(s)@sr.T;m[:3,3]=t+c-m[:3,:3]@c;return m

def compare_triangles(P,F,V,I,tolerance=2e-5):
 need(np.isfinite(P).all() and np.isfinite(V).all(),'FINITE_TRIANGLES')
 need(F.shape==I.shape and F.size>0 and F.min()>=0 and F.max()<len(P),'TRIANGLE_INDEX')
 a=P[F];b=V[I];tree=cKDTree(b.mean(1));rows=[];cols=[];errors={}
 for i,candidates in enumerate(tree.query_ball_point(a.mean(1),tolerance)):
  for j in candidates:
   error=min(float(np.linalg.norm(a[i]-np.roll(b[j],k,axis=0),axis=1).max()) for k in range(3))
   if error<=tolerance:rows.append(i);cols.append(j);errors[i,j]=error
 graph=csr_matrix((np.ones(len(rows)),(rows,cols)),shape=(len(a),len(b)));matches=maximum_bipartite_matching(graph,perm_type='column')
 need(len(matches)==len(a) and np.all(matches>=0),'WORLD_TRIANGLE_MISMATCH')
 return max(errors[i,int(j)] for i,j in enumerate(matches))

def verify(text,xml):
 need(b'<!DOCTYPE' not in xml and b'<!ENTITY' not in xml,'XML_DECLARATION');r=E.fromstring(xml,E.XMLParser(resolve_entities=False,no_network=True));schema=E.XMLSchema(E.parse(str(R/'schemas/x3d-4.0.xsd')));need(schema.validate(r),'X3D40_GRAMMAR',str(schema.error_log)[:200])
 names=[n.get('DEF') for n in r.iter() if n.get('DEF')];need(len(names)==len(set(names)),'DUPLICATE_DEF');defs={n.get('DEF'):n for n in r.iter() if n.get('DEF')}
 f=ifcopenshell.file.from_string(text);settings=ifcopenshell.geom.settings();settings.set('use-world-coords',True);products=[e for e in f.by_type('IfcProduct') if e.Representation and not e.is_a('IfcOpeningElement') and not e.is_a('IfcSpace')];it=ifcopenshell.geom.iterator(settings,f,1,include=products);need(it.initialize(),'IFC_GEOMETRY');ref={};B=np.array([[1,0,0],[0,0,1],[0,-1,0]])
 while True:
  s=it.get();ref[f.by_id(s.id).GlobalId]=(np.array(s.geometry.verts).reshape(-1,3)@B.T,np.array(s.geometry.faces,dtype=int).reshape(-1,3))
  if not it.next():break
 got={};max_extent=0.
 for n in r.iter('Transform'):
  name=n.get('DEF','')
  if not name.startswith('ifc_'):continue
  gid=ifcopenshell.guid.compress(name[4:]);need(gid not in got,'DUPLICATE_PRODUCT');need(gid in ref,'EXTRA_PRODUCT');ent=f.by_guid(gid)
  md=n.find("MetadataSet[@name='IFC']");need(md is not None and md.get('containerField')=='metadata','METADATA_ATTACHMENT')
  for k,value in [('guid',gid),('name',ent.Name or ''),('class',ent.is_a())]:need(json.loads(md.find(f"MetadataString[@name='{k}']").get('value'))==value,'METADATA_IDENTITY')
  world=np.eye(4)
  for anc in list(n.iterancestors())[::-1]+[n]:world=world@matrix(anc)
  geometries=n.findall('Shape/IndexedTriangleSet');need(bool(geometries),'MISSING_PRODUCT_GEOMETRY');allP=[];allF=[];offset=0
  for g in geometries:
   if g.get('USE'):need(g.get('USE') in defs,'DANGLING_USE');g=defs[g.get('USE')]
   P=np.fromstring(g.find('Coordinate').get('point'),sep=' ').reshape(-1,3);F=np.fromstring(g.get('index'),sep=' ',dtype=int).reshape(-1,3);W=P@world[:3,:3].T+world[:3,3];allP.append(W);allF.append(F+offset);offset+=len(P)
  P=np.concatenate(allP);F=np.concatenate(allF);V,I=ref[gid];compare_triangles(P,F,V,I);max_extent=max(max_extent,float(np.max(np.abs(P.min(0)-V.min(0)))),float(np.max(np.abs(P.max(0)-V.max(0)))));got[gid]=True
 need(set(got)==set(ref),'GEOMETRIC_COVERAGE');need(max_extent<2e-5,'EXTENT_ERROR');return {'products':len(ref),'max_extent_error_m':max_extent,'triangle_vertex_tolerance_m':2e-5,'scope':'Independent IFC world tessellation versus composed X3D transforms and winding-sensitive one-to-one triangle matching; same IfcOpenShell kernel remains a shared dependency.'}
