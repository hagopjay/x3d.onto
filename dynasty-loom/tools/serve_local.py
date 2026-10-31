#!/usr/bin/env python3
"""View a release locally, the way the Artifact host serves it. Standard library only; the files on disk are never changed.

    python3 -I dynasty-loom/tools/vendor_xite.py                                   # once, so release/v3/x_ite/ exists
    python3 -I dynasty-loom/tools/serve_local.py [--release DIR] [--port 8000]     # then open http://127.0.0.1:8000/

release/v3/index.html is an Artifact page fragment: it has no doctype and no charset, because the host wraps it in its own document.
A plain static server (python3 -m http.server) sends it bare, so the browser falls into quirks mode and reads the UTF-8 text as
windows-1252 (the bullets and dashes come out garbled). This server does what the host does: it wraps the page in a standards-mode
skeleton with <meta charset="utf-8"> (the same skeleton as tapestry/tools/artifact_csp_gate.js, without the CSP), serves only the
paths in publish.json, and gives each file the content type the publish map names (.x3d as application/xml, which X_ITE needs).
It binds 127.0.0.1 only."""
import http.server, json, os, sys
from urllib.parse import unquote, urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # dynasty-loom/
TYPES = {'.html': 'text/html; charset=utf-8', '.x3d': 'application/xml', '.json': 'application/json', '.js': 'text/javascript', '.css': 'text/css',
         '.ttf': 'font/ttf', '.woff2': 'font/woff2', '.wasm': 'application/wasm', '.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg',
         '.gif': 'image/gif', '.svg': 'image/svg+xml', '.txt': 'text/plain; charset=utf-8', '.md': 'text/markdown; charset=utf-8'}
SKELETON = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
            '<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui,sans-serif}'
            'img{max-width:100%}[hidden]{display:none!important}</style></head><body>', '</body></html>')


def arg(k, d):
    a = sys.argv[1:]
    return a[a.index(k) + 1] if k in a else d


def main():
    rel = os.path.abspath(arg('--release', os.path.join(ROOT, 'release', 'v3')))
    port = int(arg('--port', '8000'))
    pub = json.load(open(os.path.join(rel, 'publish.json'), encoding='utf-8'))
    types = {p: (v.get('contentType') if isinstance(v, dict) else None) for p, v in pub.items()}
    types['index.html'] = 'text/html; charset=utf-8'
    if not os.path.exists(os.path.join(rel, 'x_ite', 'x_ite.min.js')):
        print('note: %s/x_ite/ is missing; run tools/vendor_xite.py first (the page then falls back to jsDelivr)' % os.path.relpath(rel, os.getcwd()), file=sys.stderr)

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            u = unquote(urlsplit(self.path).path).lstrip('/') or 'index.html'
            if u == 'favicon.ico':
                self.send_response(204); self.end_headers(); return
            f = os.path.realpath(os.path.join(rel, u))
            if u not in types or not f.startswith(os.path.realpath(rel) + os.sep) or not os.path.isfile(f):
                self.send_error(404); return
            body = open(f, 'rb').read()
            if u == 'index.html': body = SKELETON[0].encode() + body + SKELETON[1].encode()
            ct = types[u] or TYPES.get(os.path.splitext(u)[1], 'application/octet-stream')
            if ct in ('text/html', 'text/plain', 'text/markdown', 'text/css', 'text/javascript'): ct += '; charset=utf-8'
            self.send_response(200)
            self.send_header('Content-Type', ct); self.send_header('Content-Length', str(len(body)))
            self.send_header('Last-Modified', self.date_time_string(int(os.path.getmtime(f))))      # cacheable, as python3 -m http.server is
            self.end_headers(); self.wfile.write(body)

        def log_message(self, fmt, *a):
            if '--quiet' not in sys.argv: super().log_message(fmt, *a)

    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print('serving %s (%d published paths) at http://127.0.0.1:%d/  (Ctrl-C stops)' % (rel, len(types), srv.server_address[1]), flush=True)
    try: srv.serve_forever()
    except KeyboardInterrupt: pass


if __name__ == '__main__':
    main()
