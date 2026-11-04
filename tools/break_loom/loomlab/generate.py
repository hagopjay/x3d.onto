"""Recipes are the source. Generated specimens are never hand edited."""
import base64,datetime,io,json,math,struct,wave,zlib
from xml.sax.saxutils import quoteattr
from .core import ROOT,canonical,sha,read,write,cards

EPOCH=1793577600
VERT='''#version 300 es
precision highp float;
in vec4 x3d_Vertex;
in vec3 x3d_Normal;
uniform mat4 x3d_ModelViewMatrix;
uniform mat4 x3d_ProjectionMatrix;
uniform mat3 x3d_NormalMatrix;
out vec3 normalV;
out vec3 localP;
void main(){normalV=normalize(x3d_NormalMatrix*x3d_Normal);localP=x3d_Vertex.xyz;gl_Position=x3d_ProjectionMatrix*x3d_ModelViewMatrix*x3d_Vertex;}
'''
FRAG='''#version 300 es
precision highp float;
in vec3 normalV;
in vec3 localP;
out vec4 fragColor;
void main(){float sampleValue=.55+.4*max(dot(normalize(normalV),normalize(vec3(-.4,.8,1.))),0.);float lines=step(.86,fract(localP.y*7.));fragColor=vec4(vec3(.05,.75,.8)*sampleValue+lines*.16,1.);}
'''
def uri(source):return 'data:text/plain;base64,'+base64.b64encode(source.encode()).decode()
def mf(s):return quoteattr(json.dumps(s))
def material(color='.08 .62 .72',emissive='0 0 0',transparency=0):
 return f'<Appearance><Material diffuseColor="{color}" emissiveColor="{emissive}" specularColor=".7 .85 .9" shininess=".6" transparency="{transparency}"/></Appearance>'
def box(pos='0 0 0',size='1 1 1',color='.08 .62 .72',meta=''):
 return f'<Transform translation="{pos}"><Shape>{meta}{material(color)}<Box size="{size}"/></Shape></Transform>'
def emblem():
 pieces=['<Shape>'+material()+ '<Sphere radius=".9"/></Shape>']
 for y,r in [(-1.1,.95),(1.1,.95),(0,1.25)]:pieces.append(f'<Transform translation="0 {y} 0"><Shape>{material(".12 .35 .45")}<Cylinder radius="{r}" height=".12"/></Shape></Transform>')
 for x in [-1.5,1.5]:pieces.append(box(f'{x} 0 0','.22 2.6 .22','.2 .75 .8'))
 return ''.join(pieces)
def palette(emission):
 faces=[]
 for i,c in enumerate(['.95 .06 .17','.02 .8 .95','.6 .08 .95']):
  x=(i-1)*1.45
  faces.append(f'<Transform translation="{x} 0 0"><Shape><Appearance><Material diffuseColor=".8 .8 .8" emissiveColor="{emission}"/></Appearance><IndexedFaceSet colorPerVertex="false" coordIndex="0 1 2 3 -1" solid="false"><Coordinate point="-.62 -1.2 0 .62 -1.2 0 .62 1.2 0 -.62 1.2 0"/><Color color="{c}"/></IndexedFaceSet></Shape></Transform>')
 return ''.join(faces)
def png():
 w=h=64;pixels=b''.join(b'\0'+b''.join(bytes((28,217,228) if (x//8+y//8)%2 else (228,42,142)) for x in range(w)) for y in range(h))
 def chunk(t,b):return struct.pack('>I',len(b))+t+b+struct.pack('>I',zlib.crc32(t+b)&0xffffffff)
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(pixels,9))+chunk(b'IEND',b'')
def audio(clipped=False):
 rate=44100;samples=[];notes=[60,64,67,72,67,64,62,60]
 for k,n in enumerate(notes):
  f=440*2**((n-69)/12)
  for i in range(rate//4):
   t=i/rate;env=min(1,t/.012)*min(1,(.25-t)/.025)
   v=(1.65 if clipped else .38)*env*math.sin(2*math.pi*f*t)
   samples.append(round(max(-1,min(1,v))*32767))
 out=io.BytesIO()
 with wave.open(out,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(struct.pack('<'+'h'*len(samples),*samples))
 return out.getvalue()
def source():
 return {'label':'Synthetic adversarial teaching fixture','records':[{'id':'a','value':4},{'id':'b','value':None},{'id':'c','value':0},{'id':'d','value':2}], 'events':[{'id':f'n{i+1}','onset':i*.25,'midi':n} for i,n in enumerate([60,64,67,72,67,64,62,60])]}
def source_meta(name,value):return f'<MetadataString name="{name}" value={mf(str(value))}/>'
def scene(cid,bad,src,wall_clock=EPOCH,epoch=EPOCH):
 timestamp=wall_clock if bad and cid=='08-clock' else epoch
 camera='0 1 0 3.141592653589793' if bad and cid=='05-camera' else '0 1 0 0'
 content=emblem();extra='';route='<ROUTE fromNode="Motion" fromField="value_changed" toNode="Subject" toField="translation"/>'
 if cid=='01-route':extra='<PositionInterpolator DEF="Motion" key="0 1" keyValue="-2.4 0 0 2.4 0 0"/>'
 if cid in ['02-raw-shader','03-reserved']:
  fragment=FRAG.replace('sampleValue','sample') if bad and cid=='03-reserved' else FRAG
  f_url=fragment if bad and cid=='02-raw-shader' else uri(fragment)
  content=f'<Shape><Appearance><Material/><ComposedShader DEF="Program" language="GLSL"><ShaderPart DEF="Vertex" type="VERTEX" url={mf(uri(VERT))}/><ShaderPart DEF="Fragment" type="FRAGMENT" url={mf(f_url)}/></ComposedShader></Appearance><Sphere radius="1.55"/></Shape>'
 if cid=='04-emissive':content=palette('1 1 1' if bad else '0 0 0')
 if cid=='06-host':
  url='data:image/png;base64,'+base64.b64encode(png()).decode() if bad else '/corpus/06-host/control/pattern.png'
  content=f'<Shape><Appearance><Material diffuseColor="1 1 1" emissiveColor="0 0 0"/><ImageTexture DEF="HostTexture" url={mf(url)}/></Appearance><Box size="3.3 2.5 .2"/></Shape>'
 if cid=='09-unknown':
  chunks=[]
  for i,r in enumerate(src['records']):
   x=(i-1.5)*1.2;v=r['value'];kind='zero' if v==0 or (v is None and bad) else 'fog' if v is None else 'bar'
   value=0 if v is None and bad else v
   metadata='<MetadataSet name="mapping">'+source_meta('row_id',r['id'])+source_meta('kind',kind)+source_meta('value',json.dumps(value))+'</MetadataSet>'
   if kind=='bar':chunks.append(box(f'{x} {v/3-1} 0',f'.75 {v*2/3} .75',meta=metadata))
   elif kind=='zero':chunks.append(box(f'{x} -1 0','.75 .025 .75','.4 .9 .65',metadata))
   else:chunks.append(f'<Transform translation="{x} -.35 0"><Shape>{metadata}{material(".6 .7 .85",".08 .12 .2",.66)}<Sphere radius=".6"/></Shape></Transform>')
  content=''.join(chunks)
 if cid=='12-score':
  content=''
  for i,e in enumerate(src['events']):
   if bad and e['id']=='n4':continue
   meta='<MetadataSet name="score">'+source_meta('event_id',e['id'])+f'<MetadataDouble name="onset" value="{e["onset"]}"/></MetadataSet>'
   height=.6+(e['midi']-60)*.12;content+=box(f'{(i-3.5)*.6} {height/2-.6} 0',f'.42 {height} .65','.1 .65 .75',meta)
 if cid=='11-ear':content=''.join(box(f'{(i-3.5)*.55} 0 0',f'.3 {1+abs(math.sin(i))} .3','.15 .75 .65') for i in range(8))
 prefix=f'''<?xml version="1.0" encoding="UTF-8"?>
<X3D profile="Immersive" version="4.0"><head><component name="Shaders" level="1"/><meta name="title" content="Break the Loom / {cid}"/><meta name="source_sha256" content="{sha(canonical(src))}"/><meta name="build_epoch" content="{timestamp}"/></head><Scene>
<WorldInfo title="Adversarial specimen / synthetic"/><Background skyColor=".017 .027 .043"/><NavigationInfo type='"NONE"' headlight="false"/><Viewpoint DEF="Camera" position="0 .3 8.5" orientation="{camera}" fieldOfView=".65"/>
<DirectionalLight direction="-.3 -.5 -1" intensity=".8"/><DirectionalLight direction=".6 .2 -1" color=".3 .6 1" intensity=".45"/>
'''
 body=(route if bad and cid=='01-route' else '')+extra+'<Transform DEF="Subject">'+content+'</Transform>'+(route if not bad and cid=='01-route' else '')
 return (prefix+body+'\n</Scene></X3D>\n').encode()
def build_case(card,variant,wall_clock=EPOCH):
 cid=card['id'];bad=variant=='mutant';src=source();xml=scene(cid,bad,src,wall_clock)
 request={'model':'synthetic-model/1','prompt_sha256':sha(b'synthetic prompt'),'parameters':{'seed':7},'input_sha256':sha(canonical(src))};key=sha(canonical(request))
 calls=[{'request':request,'request_key':key,'paid_microcredits':3000,'cache_hit':False},{'request':request,'request_key':key,'paid_microcredits':3000 if bad and cid=='10-budget' else 0,'cache_hit':not(bad and cid=='10-budget')}]
 ledger={'synthetic':True,'cap_microcredits':10000,'calls':calls}
 contract={'case_id':cid,'source_sha256':sha(canonical(src)),'palette_required':cid=='04-emissive','required_shader':cid in ['02-raw-shader','03-reserved'],'required_route':cid=='01-route','subject_visibility_required':cid not in ['01-route'],'clock_invariant':cid=='08-clock','source_date_epoch':EPOCH,'owner':card['owner'],'expected_diagnostic':card['diagnostic']}
 mapping=[{'id':r['id'],'value':0 if bad and cid=='09-unknown' and r['value'] is None else r['value']} for r in src['records']]
 files={'scene.x3d':xml,'source.json':canonical(src),'contract.json':canonical(contract),'budget.json':canonical(ledger),'mapping.json':canonical(mapping),'audio.wav':audio(bad and cid=='11-ear'),'pattern.png':png()}
 receipt={'schema':'break-loom.specimen-receipt/1','case_id':cid,'source_sha256':sha(canonical(src)),'outputs':{k:sha(v) for k,v in files.items()},'scope':'Fixture receipt; intentionally defective only in the stale-receipt mutant. No signature or authenticated origin.'}
 if bad and cid=='07-receipt':receipt['outputs']['scene.x3d']='0'*64
 files['receipt.json']=canonical(receipt)
 return files
def build():
 outputs={}
 for c in cards():
  for v in ['mutant','control']:
   dest=ROOT/'corpus'/c['id']/v;dest.mkdir(parents=True,exist_ok=True)
   for name,data in build_case(c,v).items():
    p=dest/name;p.write_bytes(data);outputs[p.relative_to(ROOT).as_posix()]={'sha256':sha(data),'bytes':len(data)}
 index={'schema':'break-loom.corpus/1','source_date_epoch':EPOCH,'cases':cards(),'outputs':outputs,'validity_definition':'XSD-valid XML. Semantic, runtime and bundle contracts are separately witnessed.','synthetic_paid_calls':True,'actual_paid_api_calls':0}
 write(ROOT/'corpus/index.json',index);return index
if __name__=='__main__':print(json.dumps({'status':'built','files':len(build()['outputs'])}))
