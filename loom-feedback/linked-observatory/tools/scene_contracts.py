"""Small independent witnesses, intended to be composed with a real schema validator."""
from pathlib import Path
from urllib.parse import urlsplit,unquote
import hashlib,json,re
from lxml import etree

def scene_assets(scene_path,root):
 scene_path=Path(scene_path).resolve();root=Path(root).resolve();r=etree.parse(str(scene_path));out=[]
 for n in r.iter():
  if n.tag not in {'ImageTexture','ImageCubeMapTexture','Background','TextureBackground','Inline','AudioClip','MovieTexture','FontStyle','FontLibrary'}:continue
  for key in ['url','topUrl','bottomUrl','frontUrl','backUrl','leftUrl','rightUrl']:
   for u in re.findall(r'"([^"]+)"',n.get(key,'')):
    parsed=urlsplit(u)
    if parsed.scheme in ('data','javascript','ecmascript'):continue
    if parsed.scheme or parsed.netloc:out.append({'url':u,'status':'external','pass':False});continue
    p=(scene_path.parent/unquote(parsed.path)).resolve()
    out.append({'url':u,'status':'inside' if p.is_relative_to(root) else 'outside','pass':p.is_relative_to(root) and p.is_file()})
 return out

def semantic_arrays(xml):
 tree=etree.fromstring(xml)
 return [(n.tag,key,' '.join(n.get(key).split())) for n in tree.iter() for key in ['point','coordIndex','colorIndex','normalIndex','texCoordIndex','color'] if n.tag in {'Coordinate','CoordinateDouble','IndexedFaceSet','IndexedLineSet','Color','ColorRGBA'} and n.get(key) is not None]

def identity_matches(data,expected):
 return isinstance(expected,str) and len(expected)==64 and hashlib.sha256(data).hexdigest()==expected

def unique_canonical_join(name,nodes):
 matches=[n for n in nodes if n.get('cls')=='NodeType' and n.get('id')==name.lower() and n.get('label','').lower()==name.lower()]
 return matches[0] if len(matches)==1 else None
