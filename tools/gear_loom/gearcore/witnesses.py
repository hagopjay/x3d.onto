"""Independent checks of emitted meshes, graph constraints and frame observations."""
import collections,math,xml.etree.ElementTree as ET
from fractions import Fraction
from .core import require,GateError,canonical,sha

def parse_scene(xml,meshes):
 tree=ET.fromstring(xml);out={}
 for ident in 'ABCD':
  coord=tree.find(f'.//Coordinate[@DEF="Coord{ident}"]');face=tree.find(f'.//IndexedFaceSet[@DEF="Mesh{ident}"]');require(coord is not None and face is not None,'MISSING_GEAR',ident)
  numbers=list(map(float,coord.get('point').split()));require(len(numbers)%3==0,'COORD_WIDTH');verts=[numbers[i:i+3] for i in range(0,len(numbers),3)];tri=[];row=[]
  for x in map(int,face.get('coordIndex').split()):
   if x==-1:require(len(row)==3,'NON_TRIANGULAR_FACE',ident);tri.append(row);row=[]
   else:row.append(x)
  require(not row,'UNTERMINATED_FACE');m=meshes[ident];require(verts==m['vertices'] and tri==m['triangles'],'SCENE_MESH_DRIFT',ident)
  out[ident]={**m,'vertices':verts,'triangles':tri}
 return tree,out

def topology(mesh):
 v=mesh['vertices'];f=mesh['triangles'];require(v and f,'EMPTY_MESH');require(all(all(math.isfinite(x) for x in p) for p in v),'NONFINITE_VERTEX')
 edges=collections.defaultdict(list);links=collections.defaultdict(lambda:collections.defaultdict(set));used=set();volume=0
 for fi,t in enumerate(f):
  require(len(t)==3 and len(set(t))==3 and all(isinstance(i,int) and 0<=i<len(v) for i in t),'FACE_INDEX',fi)
  a,b,c=[v[i] for i in t];ab=[b[i]-a[i] for i in range(3)];ac=[c[i]-a[i] for i in range(3)];cross=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
  require(sum(x*x for x in cross)>1e-18,'DEGENERATE_FACE',fi);volume+=(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6
  used.update(t)
  for i in range(3):
   x,y=t[i],t[(i+1)%3];edges[tuple(sorted((x,y)))].append((x,y));center=t[i];a1=t[(i+1)%3];b1=t[(i+2)%3];links[center][a1].add(b1);links[center][b1].add(a1)
 require(len(used)==len(v),'UNUSED_VERTEX')
 for edge,occ in edges.items():
  require(len(occ)==2,'EDGE_INCIDENCE',edge);require(occ[0]==tuple(reversed(occ[1])),'WINDING_CONFLICT',edge)
 for vertex,link in links.items():
  require(all(len(a)==2 for a in link.values()),'VERTEX_LINK',vertex);seen=set();stack=[next(iter(link))]
  while stack:
   x=stack.pop()
   if x in seen:continue
   seen.add(x);stack.extend(link[x]-seen)
  require(len(seen)==len(link),'VERTEX_PINCH',vertex)
 adjacency=collections.defaultdict(set)
 for a,b in edges:adjacency[a].add(b);adjacency[b].add(a)
 seen=set();stack=[0]
 while stack:
  x=stack.pop()
  if x in seen:continue
  seen.add(x);stack.extend(adjacency[x]-seen)
 require(len(seen)==len(v),'DISCONNECTED_MESH');euler=len(v)-len(edges)+len(f);require(euler==0,'GEAR_GENUS',euler);require(volume>0,'INVERTED_VOLUME')
 return {'vertices':len(v),'edges':len(edges),'triangles':len(f),'euler_characteristic':euler,'genus':1,'components':1,'signed_volume_mm3':volume,'edge_incidence':2,'vertex_links':'single cycles'}

def graph(plan):
 gears={g['id']:g for g in plan['gears']};require(set(gears)==set('ABCD'),'GEAR_SET');c=plan['parameters'];m=c['module_mm'];adj=collections.defaultdict(list);seen_edges=set()
 for e in plan['edges']:
  require(e['a'] in gears and e['b'] in gears and e['a']!=e['b'],'ADJACENCY_ID');a,b=gears[e['a']],gears[e['b']]
  key=tuple(sorted([a['id'],b['id']]));require(key not in seen_edges,'DUPLICATE_ADJACENCY');seen_edges.add(key)
  if e['type']=='external':
   distance=math.dist(a['center'][:2],b['center'][:2]);expected=m*(a['teeth']+b['teeth'])/2
   require(abs(distance-expected)<1e-8 and abs(a['center'][2]-b['center'][2])<1e-8,'CENTER_DISTANCE',e)
   multiplier=-Fraction(a['teeth'],b['teeth'])
  elif e['type']=='rigid':
   require(math.dist(a['center'][:2],b['center'][:2])<1e-8,'COAXIALITY');multiplier=Fraction(1)
  else:raise GateError('EDGE_TYPE')
  adj[a['id']].append((b['id'],multiplier));adj[b['id']].append((a['id'],1/multiplier))
 ratios={'A':Fraction(1)};pending=['A']
 while pending:
  a=pending.pop()
  for b,k in adj[a]:
   value=ratios[a]*k
   if b in ratios:require(ratios[b]==value,'RATIO_CYCLE')
   else:ratios[b]=value;pending.append(b)
 require(set(ratios)==set(gears),'DISCONNECTED_TRAIN')
 for ident,r in ratios.items():require(Fraction(*gears[ident]['ratio'])==r,'RATIO_DECLARATION',ident)
 return {'ratios':{k:[r.numerator,r.denominator] for k,r in ratios.items()},'connected':True,'external_meshes':sum(e['type']=='external' for e in plan['edges']),'rigid_links':sum(e['type']=='rigid' for e in plan['edges'])}

def footprint(mesh,g):
 import numpy as np
 import shapely
 from shapely.geometry import Polygon
 n=mesh['ring_size'];v=np.array(mesh['vertices']);require(len(v)==8*n,'RING_STRUCTURE');outer=v[n:2*n,:2];p=Polygon(outer);require(p.is_valid and p.area>0,'PROFILE_SELF_INTERSECTION')
 radii=np.linalg.norm(outer,axis=1);at_tip=np.abs(radii-g['tip_radius'])<1e-7;groups=sum(bool(at_tip[i]) and not bool(at_tip[(i-1)%n]) for i in range(n));require(groups==g['teeth'],'TOOTH_COUNT',{'declared':g['teeth'],'measured':groups})
 require(abs(float(radii.min())-g['root_radius'])<1e-7,'ROOT_RADIUS');require(abs(float(radii.max())-g['tip_radius'])<1e-7,'TIP_RADIUS')
 # Every delivered triangle must lie inside this conservative XY footprint.
 triangles=v[np.array(mesh['triangles']),:2];polys=shapely.polygons(triangles);areas=shapely.area(polys);nonzero=polys[areas>1e-10];contained=shapely.covered_by(nonzero,p.buffer(1e-7));require(bool(contained.all()),'FOOTPRINT_CONTAINMENT')
 rotated=shapely.affinity.rotate(p,2*math.pi/g['teeth'],origin=(0,0),use_radians=True)
 periodic_error=p.hausdorff_distance(rotated);require(periodic_error<1e-7,'TOOTH_PERIODICITY')
 return p,{'teeth_counted':groups,'profile_vertices':n,'profile_valid':True,'all_face_projections_contained':True,'tooth_periodicity_error_mm':periodic_error,'z_min':float(v[:,2].min()),'z_max':float(v[:,2].max())}

def clearance(poly_a,poly_b,a,b,margin=0.0001):
 from shapely.affinity import rotate,translate
 period=2*math.pi/a['teeth'];ratio=-a['teeth']/b['teeth'];phase_a=a['phase'];phase_b=b['phase'];speed_bound=a['tip_radius']+abs(ratio)*b['tip_radius'];leaves=[];samples=[]
 def check(lo,hi,depth):
  mid=(lo+hi)/2
  pa=translate(rotate(poly_a,phase_a+mid,origin=(0,0),use_radians=True),xoff=a['center'][0],yoff=a['center'][1]);pb=translate(rotate(poly_b,phase_b+ratio*mid,origin=(0,0),use_radians=True),xoff=b['center'][0],yoff=b['center'][1])
  distance=pa.distance(pb);samples.append(distance)
  require(distance>0,'INTERPENETRATION',{'driver_angle':mid,'overlap_mm2':pa.intersection(pb).area})
  bound=distance-speed_bound*(hi-lo)/2-margin
  if bound>0:leaves.append({'lo':lo,'hi':hi,'midpoint_distance_mm':distance,'clearance_lower_bound_mm':bound});return
  require(depth<18,'CLEARANCE_UNRESOLVED',{'lo':lo,'hi':hi,'distance':distance});check(lo,mid,depth+1);check(mid,hi,depth+1)
 check(0,period,0)
 return {'status':'pass','pair':[a['id'],b['id']],'period_rad':period,'motion_bound_mm_per_rad':speed_bound,'numerical_reserve_mm':margin,'intervals':leaves,'interval_count':len(leaves),'queries':len(samples),'minimum_sampled_distance_mm':min(samples),'minimum_certified_lower_bound_mm':min(x['clearance_lower_bound_mm'] for x in leaves),'coverage':'Entire repeating tooth cycle, including the intervals between samples. Reverse traverses the same certified set.','scope':'Floating-point conservative bound on serialized tooth-body footprints. Not an exact-arithmetic theorem or manufacturing certification.'}

def motion(trace,plan):
 rows=trace['samples'];require(len(rows)>=30,'INSUFFICIENT_FRAMES');t=[r['t_ms']/1000 for r in rows];require(all(t[i+1]>t[i] for i in range(len(t)-1)),'FRAME_CLOCK_ORDER');duration=t[-1]-t[0];require(duration>=2,'INSUFFICIENT_DURATION')
 max_gap=max(t[i+1]-t[i] for i in range(len(t)-1));rpm=trace['requested_rpm'];require(abs(rpm)>0,'ZERO_REFERENCE_SPEED');require(max_gap*abs(rpm)*2*math.pi/60<math.pi*.85,'ANGULAR_ALIAS_RISK')
 ratios=graph(plan)['ratios'];result={};mean_t=sum(t)/len(t);den=sum((x-mean_t)**2 for x in t)
 for j,ident in enumerate('ABCD'):
  angles=[rows[0]['angles'][j]]
  for i in range(1,len(rows)):
   d=rows[i]['angles'][j]-rows[i-1]['angles'][j];d=math.atan2(math.sin(d),math.cos(d));angles.append(angles[-1]+d)
  mean=sum(angles)/len(angles);slope=sum((tt-mean_t)*(aa-mean) for tt,aa in zip(t,angles))/den;residual=max(abs(aa-(mean+slope*(tt-mean_t))) for tt,aa in zip(t,angles));expected=rpm*math.tau/60*float(Fraction(*ratios[ident]));require(abs(slope-expected)<=max(1e-5,abs(expected)*.0002),'ANGULAR_SPEED',{'gear':ident,'measured':slope,'expected':expected});require(residual<.0001,'NONUNIFORM_MOTION',ident)
  result[ident]={'rad_per_second':slope,'rpm':slope*60/math.tau,'expected_rpm':expected*60/math.tau,'max_residual_rad':residual}
 for ident in 'ABCD':result[ident]['measured_ratio_to_A']=result[ident]['rad_per_second']/result['A']['rad_per_second'];result[ident]['expected_ratio_to_A']=float(Fraction(*ratios[ident]))
 gears={g['id']:g for g in plan['gears']};phase_error=0
 for row in rows:
  for edge in plan['edges']:
   a,b=gears[edge['a']],gears[edge['b']];da=row['angles'][ord(a['id'])-65]-a['phase'];db=row['angles'][ord(b['id'])-65]-b['phase']
   error=a['teeth']*da+b['teeth']*db if edge['type']=='external' else db-da
   phase_error=max(phase_error,abs(math.atan2(math.sin(error),math.cos(error))))
 require(phase_error<.00002,'MESH_PHASE',phase_error)
 return {'status':'pass','frames':len(rows),'duration_seconds':duration,'max_frame_gap_seconds':max_gap,'gears':result,'maximum_phase_invariant_error_rad':phase_error,'scope':'OLS of unwrapped live X_ITE rotation observations against requestAnimationFrame timestamps, plus adjacency phase invariants; not values echoed from requested ratios.'}
