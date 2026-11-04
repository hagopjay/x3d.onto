"""Portable predicates learned on Gobbler. Narrow checks, not an X3D validator."""
import hashlib,re,xml.etree.ElementTree as E

def inspect(xml,scene_sha256,expanding_shaders=()):
 failures=[]
 if hashlib.sha256(xml).hexdigest()!=scene_sha256:failures.append('L-ID: scene receipt is stale')
 root=E.fromstring(xml);seen=set();inlines={n.get('DEF') for n in root.iter('Inline')}
 for n in root.iter():
  d=n.get('DEF')
  if d:
   if d in seen:failures.append('L-DEF: duplicate name')
   seen.add(d)
  if n.tag=='ShaderPart':
   for m in re.finditer(r'smoothstep\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,',n.text or ''):
    if float(m[1])>=float(m[2]):failures.append('L-GLSL: unordered literal edges')
  if n.tag=='ROUTE' and n.get('toNode') in inlines and n.get('toField') in ('load','set_load'):failures.append('L-OWNER: second Inline load owner')
 for shape in root.iter('Shape'):
  mesh=shape.find('IndexedFaceSet')
  if mesh is None:continue
  faces=[f.split() for f in mesh.get('coordIndex','').split('-1') if f.strip()]
  if not any(len(set(f))<3 for f in faces):continue
  shader=shape.find('Appearance/ComposedShader');name=(shader.get('DEF') or shader.get('USE')) if shader is not None else None
  if name not in expanding_shaders:failures.append('L-RIBBON: unexplained zero-area topology')
  if mesh.find('Tangent') is None:failures.append('L-RIBBON: no explicit basis')
 return failures

def accumulated_opacity(transparency,layers):
 if not 0<=transparency<=1 or isinstance(layers,bool) or not isinstance(layers,int) or layers<0:raise ValueError('Invalid alpha contract')
 return 1-transparency**layers

def observed_arrival(expected,observed,tolerance):
 """Independent numeric receipt check; a label or finite pose alone is insufficient."""
 import math
 if len(expected)!=3 or len(observed)!=3 or not math.isfinite(tolerance) or tolerance<=0:return False
 if not all(math.isfinite(x) for x in expected+observed):return False
 return math.dist(expected,observed)<=tolerance
