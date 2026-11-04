"""Reusable, fail-closed fidelity predicates. Models do not assign numeric grades."""
import math,hashlib
import numpy as np
class FidelityError(RuntimeError):pass
def need(value,code):
 if not value:raise FidelityError(code)
def bake_binding(receipt,actual):
 need(receipt['schema']=='loomsong.radiance/4','BAKE_SCHEMA')
 for key in ['scene_sha256','baker_sha256','proxy_baker_sha256']:need(receipt['binding'][key]==actual[key],'STALE_BAKE:'+key)
 need(set(receipt['outputs'])==set(actual['outputs']),'BAKE_OUTPUT_COVERAGE')
 for key,digest in receipt['outputs'].items():need(digest==actual['outputs'][key],'BAKE_OUTPUT_HASH:'+key)
def atlas_layout(a):
 need(a.shape==(780,256,4),'PREFILTER_LAYOUT')
 need(np.all(a[:,:,3]>0),'RGBM_ZERO_MULTIPLIER')
 for i in range(6):
  tile=a[i*130:(i+1)*130]
  need(np.array_equal(tile[0],tile[1]) and np.array_equal(tile[-1],tile[-2]),'PREFILTER_GUTTER')
 decoded=a[:,:,:3].astype(float)/255*a[:,:,3:4]/255*16
 need(decoded.max()>2 and decoded.max()<16,'HDR_RANGE')
 need(np.mean(abs(decoded[1:129]-decoded[651:779]))>.015,'ROUGHNESS_LEVELS_IDENTICAL')
 return {'decoded_peak':float(decoded.max()),'level_difference':float(np.mean(abs(decoded[1:129]-decoded[651:779])))}
def dfg_reference(nv,r,count=256):
 a=r*r;k=a/2;vx=math.sqrt(1-nv*nv);A=B=0.
 for i in range(count):
  bits=i;u=0.;scale=.5
  while bits:u+=(bits%2)*scale;bits//=2;scale/=2
  phi=2*math.pi*(i+.5)/count;hz=math.sqrt((1-u)/(1+(a*a-1)*u));hx=math.sqrt(1-hz*hz)*math.cos(phi)
  vh=max(vx*hx+nv*hz,0);nl=max(2*vh*hz-nv,0)
  if nl<=0:continue
  gv=nv/(nv*(1-k)+k);gl=nl/(nl*(1-k)+k);vis=gv*gl*vh/max(hz*nv,1e-8);f=(1-vh)**5;A+=(1-f)*vis;B+=f*vis
 return np.array([A/count,B/count])
def brdf_table(a):
 need(a.shape==(128,128,3),'BRDF_LAYOUT');errors=[]
 for y in [3,19,47,89,122]:
  for x in [5,23,60,96,125]:errors.append(float(np.max(abs(a[y,x,:2]/255-dfg_reference((x+.5)/128,(y+.5)/128)))))
 need(max(errors)<=.0021,'BRDF_REFERENCE_MISMATCH');return {'probes':len(errors),'maximum_linear_error':max(errors)}
def texture_contract(tree):
 keys=['u_environment','u_shadowmap','u_prefilter','u_irradiance','u_brdf','u_material','u_params']
 for key in keys:
  nodes=tree.findall('.//ImageTexture[@DEF="Shared_'+key+'"]');need(len(nodes)==1,'SHARED_TEXTURE_OWNER:'+key)
  tp=nodes[0].find('TextureProperties');need(tp is not None and tp.get('generateMipMaps')=='false','DATA_TEXTURE_MIP_BLEED:'+key)
  url=nodes[0].get('url');need(len([n for n in tree.iter('ImageTexture') if n.get('url')==url])==1,'DUPLICATE_TEXTURE_ALLOCATION:'+key)
  need(len(tree.findall('.//ImageTexture[@USE="Shared_'+key+'"]'))>=2,'TEXTURE_NOT_SHARED:'+key)
 return {'shared_textures':len(keys),'mipmaps':'disabled on packed/data maps'}
def profile_contract(p):
 need(p['schema']=='loomsong.profile/4','PROFILE_SCHEMA')
 for name in ['draw_intervals','cpu_display_submission','cpu_scene_update','gpu']:
  s=p[name];need(type(s['samples']) is int and s['samples']>=0,'PROFILE_SAMPLE_COUNT')
  values=[s[k] for k in ['median_ms','p95_ms','p99_ms']]
  if s['samples']==0:need(all(v is None for v in values),'UNKNOWN_IS_NOT_ZERO')
  else:need(all(type(v) in [float,int] and math.isfinite(v) and v>=0 for v in values),'NONFINITE_PROFILE');need(values==sorted(values),'PROFILE_QUANTILES')
 if not p['gpu']['available']:need(p['gpu']['samples']==0,'UNAVAILABLE_GPU_MEASURED')
 return True
def camera_handoff(before,after,tolerance=1e-6):
 for key in ['position','target']:
  need(len(before[key])==len(after[key])==3,'CAMERA_VECTOR')
  need(all(math.isfinite(x) for x in before[key]+after[key]),'CAMERA_FINITE')
  need(max(abs(a-b) for a,b in zip(before[key],after[key]))<=tolerance,'CAMERA_HANDOFF_JUMP')
 need(abs(before['fieldOfView']-after['fieldOfView'])<=tolerance,'CAMERA_HANDOFF_LENS')
 return True
