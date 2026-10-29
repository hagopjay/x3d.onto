"""Delta debugging (Zeller and Hildebrandt's ddmin) over the parts of an X3D scene: first whole elements under <Scene> (removing an element
removes its subtree), then attributes. The predicate takes a LIST of candidate XML strings and returns a list of booleans, so a round of
ddmin is tested in one batch (one X_ITE page call instead of one per candidate).
  minimize(xml, holds_batch) -> smallest xml found for which holds stays true (1-minimal in the units tried)"""
from lxml import etree

KEEP_TAGS = {"X3D", "Scene", "head"}


def _units(root):
    els = [e for e in root.iter() if isinstance(e.tag, str) and e.tag not in KEEP_TAGS]
    return els


def _render(xml, drop_el=(), drop_attr=()):
    root = etree.fromstring(xml.encode())
    els = _units(root)
    for i, a in drop_attr:
        if i < len(els) and a in els[i].attrib: del els[i].attrib[a]
    for i in sorted(drop_el, reverse=True):
        e = els[i]
        if e.getparent() is not None: e.getparent().remove(e)
    return pretty(etree.tostring(root, encoding="unicode"))


def _hoist(xml, i):
    """Replace element i by its own children (a wrapper removed, its content kept in place)."""
    root = etree.fromstring(xml.encode()); els = _units(root)
    if i >= len(els): return None
    e = els[i]; p = e.getparent()
    kids = [c for c in e if isinstance(c.tag, str)]
    if p is None or not kids: return None
    at = list(p).index(e)
    for k, c in enumerate(kids): p.insert(at + k, c)
    p.remove(e)
    return pretty(etree.tostring(root, encoding="unicode"))


def ddmin(n_units, test_batch, max_rounds=200):
    """Classic ddmin on unit indices 0..n-1. test_batch(list of kept-index lists) -> list of bool. Returns kept indices."""
    cur = list(range(n_units)); n = 2; rounds = 0
    while len(cur) >= 2 and rounds < max_rounds:
        rounds += 1
        size = max(1, len(cur) // n)
        chunks = [cur[i:i + size] for i in range(0, len(cur), size)]
        comps = [[u for u in cur if u not in set(c)] for c in chunks]
        cands = chunks + comps
        res = test_batch(cands)
        hit = next((i for i, r in enumerate(res) if r), None)
        if hit is not None and hit < len(chunks):
            cur, n = chunks[hit], 2
        elif hit is not None:
            cur, n = comps[hit - len(chunks)], max(n - 1, 2)
        elif n < len(cur):
            n = min(len(cur), 2 * n)
        else:
            break
    if len(cur) == 1 and test_batch([[]])[0]: cur = []
    return cur


def minimize(xml, holds_batch, attrs=True):
    """Shrink xml while holds_batch([xml]) stays true. Elements first, then attributes."""
    if not holds_batch([xml])[0]: return xml
    root = etree.fromstring(xml.encode()); els = _units(root); N = len(els)
    def as_xml_el(kept):
        ks = set(kept); return _render(xml, drop_el=[i for i in range(N) if i not in ks])
    kept = ddmin(N, lambda cands: holds_batch([as_xml_el(k) for k in cands]))
    cur = as_xml_el(kept)
    # greedy passes: delete one element, or hoist one wrapper (replace it by its children), until neither helps
    changed = True
    while changed:
        changed = False
        r = etree.fromstring(cur.encode()); n = len(_units(r))
        cands = [_render(cur, drop_el=[i]) for i in range(n)] + [h for h in (_hoist(cur, i) for i in range(n)) if h]
        res = holds_batch(cands) if cands else []
        for c, ok in zip(cands, res):
            if ok: cur, changed = c, True; break
    r = etree.fromstring(cur.encode())
    if r.get("profile") not in (None, "Full"):
        r.set("profile", "Full"); c2 = pretty(etree.tostring(r, encoding="unicode"))
        if holds_batch([c2])[0]: cur = c2
    if attrs:
        r = etree.fromstring(cur.encode()); els = _units(r)
        A = [(i, a) for i, e in enumerate(els) for a in e.attrib if a not in ("DEF", "USE")]
        A += [(i, a) for i, e in enumerate(els) for a in e.attrib if a in ("DEF", "USE")]
        base = cur
        def as_xml_at(kept):
            ks = set(kept); return _render(base, drop_attr=[A[j] for j in range(len(A)) if j not in ks])
        if A:
            kept = ddmin(len(A), lambda cands: holds_batch([as_xml_at(k) for k in cands]))
            cur = as_xml_at(kept)
        r = etree.fromstring(cur.encode())
        hd = r.find("head")
        if hd is not None and len(hd) == 0:
            r.remove(hd); c2 = pretty(etree.tostring(r, encoding="unicode"))
            if holds_batch([c2])[0]: cur = c2
    return cur


def pretty(xml):
    """One element per line, so XSD line numbers name one element."""
    root = etree.fromstring(xml.encode() if isinstance(xml, str) else xml, etree.XMLParser(remove_blank_text=True))
    for e in root.iter():
        if isinstance(e.tag, str) and e.text is not None and not e.text.strip(): e.text = None
        if e.tail is not None and not e.tail.strip(): e.tail = None
    etree.indent(root, "  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + etree.tostring(root, encoding="unicode") + "\n"
