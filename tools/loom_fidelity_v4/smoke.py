from pathlib import Path
import copy,json,xml.etree.ElementTree as E
import numpy as np
from PIL import Image
from fidelity_contract import *
R=Path(__file__).resolve().parent
atlas=np.array(Image.open(R/'fixtures/ibl-prefilter.png'));lut=np.array(Image.open(R/'fixtures/brdf-lut.png'));atlas_layout(atlas);brdf_table(lut)
keys=['u_environment','u_shadowmap','u_prefilter','u_irradiance','u_brdf','u_material','u_params'];tree=E.Element('SyntheticTextureGraph')
for key in keys:
 n=E.SubElement(tree,'ImageTexture',DEF='Shared_'+key,url=key);E.SubElement(n,'TextureProperties',generateMipMaps='false')
 for i in range(2):E.SubElement(tree,'ImageTexture',USE='Shared_'+key)
texture_contract(tree)
empty={'samples':0,'median_ms':None,'p95_ms':None,'p99_ms':None};profile={'schema':'loomsong.profile/4',**{k:dict(empty) for k in ['draw_intervals','cpu_display_submission','cpu_scene_update']},'gpu':{**empty,'available':False}};profile_contract(profile)
camera={'position':[1.,2.,3.],'target':[0.,0.,0.],'fieldOfView':.6};camera_handoff(camera,camera)
receipt={'schema':'loomsong.radiance/4','binding':{'scene_sha256':'a'*64,'baker_sha256':'b'*64,'proxy_baker_sha256':'c'*64},'outputs':{'texture':'d'*64}};actual={**receipt['binding'],'outputs':dict(receipt['outputs'])};bake_binding(receipt,actual)
caught=[]
def reject(name,fn):
 try:fn()
 except FidelityError as e:caught.append({'case':name,'diagnostic':str(e)});return
 raise RuntimeError('SURVIVING_CONTROL:'+name)
bad=copy.deepcopy(receipt);bad['binding']['scene_sha256']='0'*64;reject('stale bake',lambda:bake_binding(bad,actual))
reject('white BRDF',lambda:brdf_table(np.full_like(lut,255)));reject('black BRDF',lambda:brdf_table(np.zeros_like(lut)))
bad=atlas.copy();bad[:,:,3]=0;reject('missing RGBM multiplier',lambda:atlas_layout(bad))
reject('identical roughness levels',lambda:atlas_layout(np.concatenate([atlas[:130]]*6)))
bad=atlas.copy();bad[0,10,0]^=255;reject('bad atlas gutter',lambda:atlas_layout(bad))
bad=copy.deepcopy(tree);bad.find('.//TextureProperties').set('generateMipMaps','true');reject('mip bleed',lambda:texture_contract(bad))
bad=copy.deepcopy(tree);n=copy.deepcopy(bad.find('.//ImageTexture'));n.set('DEF','Duplicate');bad.append(n);reject('duplicate owner',lambda:texture_contract(bad))
bad=copy.deepcopy(profile);bad['gpu']['median_ms']=0;reject('unknown is zero',lambda:profile_contract(bad))
bad=copy.deepcopy(profile);bad['gpu'].update(samples=2,median_ms=1,p95_ms=2,p99_ms=3);reject('unavailable timing',lambda:profile_contract(bad))
bad=copy.deepcopy(camera);bad['position'][0]+=.2;reject('pose jump',lambda:camera_handoff(camera,bad))
bad=copy.deepcopy(camera);bad['fieldOfView']=.9;reject('lens jump',lambda:camera_handoff(camera,bad))
need(len(caught)==12,'CONTROL_COUNT');print(json.dumps({'status':'pass','negative_controls':caught,'optimized':not __debug__,'scope':'Production numeric and structural predicates; synthetic profile/binding/graph controls are not hardware or renderer runs.'}))
