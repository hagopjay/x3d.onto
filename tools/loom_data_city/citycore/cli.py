"""Reusable gate CLI: no web server, graphics library or third-party dependency."""
import argparse,json,sys
from pathlib import Path
from .core import CityError,sha
from .gates import verify,verify_scene
def main():
 p=argparse.ArgumentParser(description='Verify CSV-to-manifest-to-X3D truth and lineage.');p.add_argument('source');p.add_argument('manifest');p.add_argument('--scene');a=p.parse_args()
 try:
  raw=Path(a.source).read_bytes();m=json.loads(Path(a.manifest).read_text());results={'truth':verify(raw,m)}
  if a.scene:results['geometry']=verify_scene(Path(a.scene).read_bytes(),m)
  print(json.dumps({'status':'pass','source_sha256':sha(raw),'results':results},indent=2));return 0
 except CityError as e:print(json.dumps({'status':'fail','diagnostic':e.code,'detail':e.detail}),file=sys.stderr);return 1
 except Exception as e:print(json.dumps({'status':'error','instrument_error':str(e)}),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
