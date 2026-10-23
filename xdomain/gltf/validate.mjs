// usage: node validate.mjs <dir>   -> NDJSON on stdout, one line per *.gltf: {file, ms, errors, warnings, infos, hints, messages:[{code,severity,pointer,message}]}
import fs from 'node:fs'; import path from 'node:path'; import { createRequire } from 'node:module';
const require = createRequire(import.meta.url); const v = require('gltf-validator');
const dir = process.argv[2];
for (const f of fs.readdirSync(dir).filter(x => x.endsWith('.gltf')).sort()) {
  const s = fs.readFileSync(path.join(dir, f), 'utf8'); const t0 = performance.now();
  try {
    const r = await v.validateString(s, { uri: f, maxIssues: 0, externalResourceFunction: () => Promise.reject(new Error('no external')) });
    const i = r.issues; console.log(JSON.stringify({ file: f, ms: +(performance.now() - t0).toFixed(2), errors: i.numErrors, warnings: i.numWarnings, infos: i.numInfos, hints: i.numHints, version: v.version(), messages: i.messages.map(m => ({ code: m.code, severity: m.severity, pointer: m.pointer, message: m.message })) }));
  } catch (e) { console.log(JSON.stringify({ file: f, ms: +(performance.now() - t0).toFixed(2), crash: String(e).slice(0, 200) })); }
}
