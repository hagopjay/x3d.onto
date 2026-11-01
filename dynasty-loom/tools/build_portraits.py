#!/usr/bin/env python3
"""Copy the portraits a release shows, and only those, from the portraits thread's manifest. Standard library only; deterministic.

    python3 -I dynasty-loom/tools/build_portraits.py --manifest PATH/manifest.json --cards DIR --out DIR [--placeholders DIR]

The portraits thread (another workspace) owns manifest.json and its cache/: it writes one entry per person (id, usually the Wikidata QID; name;
family; status pending, ok or rejected; label; the cut-out and thumb paths under cache/<id>/). This stage reads only manifest.json and the files
it names, and writes:
  <out>/portraits/<id>/<path under cache/<id>/>   each named file, byte for byte (v1/cutout-768.webp and v1/thumb-256.webp for an AI portrait,
                                                    monogram/cutout-768.webp and monogram/thumb-256.webp for a monogram card)
  <out>/portraits/<id>/placeholder/...            with --placeholders (make_placeholders.py's out/): the shared silhouette with the person's
                                                    initials, in place of the monogram card, for every entry that is not ok
  <out>/portraits.json                            id -> name, family, label, status, kind (ai-portrait, placeholder or monogram), the published
                                                    paths and their sha256; plus the manifest's own sha256 and its generated time
Rules (the build stops when one fails):
  * kind is ai-portrait only for status ok with files outside monogram/; every other status must name monogram/ files, so a pending or
    rejected entry can never show a face;
  * every entry must carry a label (the page shows it on hover and on the card);
  * a person must be in the release's cards (--cards: <family>.cards.json), which hold no one possibly living; anyone else is left out and
    listed under skipped;
  * every path stays under cache/<id>/ (no '..', no absolute paths);
  * a placeholder is one plain silhouette for everyone, never a likeness, and is used only for a status other than ok.
A fuller manifest needs no code change: run this again, then the hypersphere build (its plates read portraits.json) and the publish stage."""
import hashlib, json, os, shutil, sys

FAMILIES = ['rothschild', 'habsburg', 'darwin_wedgwood']
ASOF, LIVING_YEARS = 2026, 110


def arg(k, d=None):
    a = sys.argv[1:]
    return a[a.index(k) + 1] if k in a else d


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def main():
    man_p, cards_d, out, ph_d = arg('--manifest'), arg('--cards'), arg('--out'), arg('--placeholders')
    if not (man_p and cards_d and out): sys.exit(__doc__)
    ph = {e['id']: e for e in json.load(open(os.path.join(ph_d, 'placeholders.json'), encoding='utf-8'))['people']} if ph_d else {}
    root = os.path.dirname(os.path.abspath(man_p)); man = json.load(open(man_p, encoding='utf-8'))
    people = {}
    for f in FAMILIES:
        for pid, p in json.load(open(os.path.join(cards_d, f + '.cards.json'), encoding='utf-8'))['people'].items(): people[pid] = (f, p)
    dst_root = os.path.join(out, 'portraits')
    if os.path.isdir(dst_root): shutil.rmtree(dst_root)
    res, skipped, problems = {}, [], []
    for e in sorted(man['people'], key=lambda x: x['id']):
        pid = e['id']
        if pid not in people: skipped.append(dict(id=pid, name=e.get('name'), why='not in the release cards')); continue
        fam, p = people[pid]
        born, died = p.get('born'), p.get('died')
        if died in (None, '') and isinstance(born, int) and born >= ASOF - LIVING_YEARS: problems.append('%s: possibly living' % pid); continue
        if not (e.get('label') or '').strip(): problems.append('%s: no label' % pid); continue
        status = e.get('status'); paths = {k: e.get(k) for k in ('cutout', 'thumb')}
        for k, rel in paths.items():
            if not rel or os.path.isabs(rel) or '..' in rel.split('/') or not rel.startswith('cache/%s/' % pid): problems.append('%s: %s path %r is not under cache/%s/' % (pid, k, rel, pid))
        if any('not under' in x for x in problems if x.startswith(pid + ':')): continue
        mono = all('/monogram/' in rel for rel in paths.values())
        if status == 'ok' and not mono: kind = 'ai-portrait'
        elif mono: kind = 'monogram'
        else: problems.append('%s: status %s names non-monogram files (a face may only show for status ok)' % (pid, status)); continue
        item = dict(id=pid, name=e.get('name') or p.get('name'), family=fam, label=e['label'].strip(), status=status, kind=kind, sha256={})
        srcs = {k: (os.path.join(root, rel), 'portraits/' + rel[len('cache/'):]) for k, rel in paths.items()}
        if kind == 'monogram' and pid in ph:   # the silhouette stands in for the monogram card; its label says what it is
            q = ph[pid]
            item.update(kind='placeholder', label=q['label'])
            srcs = {k: (os.path.join(ph_d, q[k]), 'portraits/%s/placeholder/%s' % (pid, os.path.basename(q[k]))) for k in ('cutout', 'thumb')}
        for k, (src, pub) in srcs.items():
            if not os.path.isfile(src): problems.append('%s: %s missing (%s)' % (pid, k, src)); break
            d = os.path.join(out, pub); os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copyfile(src, d)
            item[k] = pub; item['sha256'][pub] = sha(d)
        else:
            res[pid] = item
    if problems: sys.exit('portraits: ' + '; '.join(problems))
    doc = dict(version='portraits/1', made_by='tools/build_portraits.py', manifest=dict(sha256=sha(man_p), generated=man.get('generated'), version=man.get('version'), entries=len(man['people'])),
               counts=dict(people=len(res), ai_portrait=sum(1 for x in res.values() if x['kind'] == 'ai-portrait'), placeholder=sum(1 for x in res.values() if x['kind'] == 'placeholder'),
                           monogram=sum(1 for x in res.values() if x['kind'] == 'monogram'),
                           by_status={s: sum(1 for x in res.values() if x['status'] == s) for s in sorted({x['status'] for x in res.values()})}),
               rule='kind ai-portrait only for status ok; pending and rejected entries show the shared silhouette placeholder (or their monogram card without --placeholders), never a face; every image carries its label', people=res, skipped=skipped)
    json.dump(doc, open(os.path.join(out, 'portraits.json'), 'w', encoding='utf-8'), indent=1, sort_keys=True, ensure_ascii=False)
    print(json.dumps(dict(out=out, **doc['counts'], skipped=len(skipped))))


if __name__ == '__main__':
    main()
