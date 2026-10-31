#!/usr/bin/env python3
"""Dynasty Loom portraits: cache-first Gemini restyles of public-domain portraits.

The cache is the point. A person whose cache/<id>/v1/portrait.png exists is never
requested again; --redo <id> writes the next vN/ and never touches an older one.
Every Gemini call is logged to requests.jsonl first, and the script refuses to
call when that log holds 60 calls, or 2 for the person.

  portraits.py refs [ids...]        resolve Wikidata P18 + Commons licence, download reference
  portraits.py gen [ids...] [--redo ID] [--dry-run]
  portraits.py review ID --verdict pass|fail --notes "..." [--version vN]
  portraits.py post                 cut-outs, thumbs, monograms, manifest.json, contact-v1.png

The API key is read from GEMINI_API_KEY2 / GEMINI_API_KEY and never printed or written.
"""
import argparse, base64, datetime, hashlib, html, io, json, os, re, sys, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
LOG = ROOT / "requests.jsonl"
PEOPLE = json.loads((ROOT / "people.json").read_text())["people"]
BY_ID = {p["id"]: p for p in PEOPLE}
OVERRIDES = ROOT / "refs.json"   # hand-picked Commons files, or null for "no likeness survives"
MODEL = "gemini-3-pro-image"
BUDGET, PER_PERSON = 60, 2
UA = "DynastyLoomPortraits/1.0 (genealogy visualisation; contact via github.com/hagopjay)"
FAMILY_COLOR = {"rothschild": "#9e1b1b", "habsburg": "#b8860b", "darwin": "#2f6b3a", "wedgwood": "#3f74a8"}  # the cards' dyes
OK_LICENCES = ("public domain", "pd", "cc0", "cc-pd", "pdm")


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def get(url, binary=False, tries=40):
    """Polite fetch: Wikimedia rate-limits the shared egress, so honour Retry-After."""
    import time
    for i in range(tries):
        time.sleep(3)   # pace every request; the container shares its egress IP
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            return data if binary else json.loads(data)
        except urllib.error.HTTPError as e:
            if e.code != 429 or i == tries - 1:
                raise
            time.sleep(min(120, int(e.headers.get("retry-after") or 10) + 2 + 5 * i))


def strip_html(s):
    return html.unescape(re.sub(r"<[^>]+>", "", str(s) if s is not None else "")).strip()


def log_lines():
    if not LOG.exists():
        return []
    return [json.loads(l) for l in LOG.read_text().splitlines() if l.strip()]


def versions(pid):
    d = CACHE / pid
    return sorted((int(p.name[1:]) for p in d.glob("v[0-9]*") if (p / "portrait.png").exists()), key=int) if d.exists() else []


# ---------------------------------------------------------------- references

def commons_files(ids):
    """One Wikidata call for every id's P18; refs.json overrides (null = no likeness survives)."""
    overrides = json.loads(OVERRIDES.read_text()) if OVERRIDES.exists() else {}
    ask = [i for i in ids if i not in overrides]
    out = {i: overrides[i] for i in ids if i in overrides}
    for k in range(0, len(ask), 50):
        d = get("https://www.wikidata.org/w/api.php?action=wbgetentities&props=claims&format=json&ids=" + "|".join(ask[k:k + 50]))
        for i, e in d["entities"].items():
            p18 = e.get("claims", {}).get("P18", [])
            out[i] = p18[0]["mainsnak"]["datavalue"]["value"] if p18 else None
    return out


def commons_info(fnames):
    """One Commons call per 50 files: url, 1280px thumb (a Wikimedia standard size; others get 429), licence metadata."""
    out = {}
    titles = sorted({"File:" + f.replace("_", " ") for f in fnames if f})
    for k in range(0, len(titles), 50):
        q = urllib.parse.urlencode({"action": "query", "titles": "|".join(titles[k:k + 50]), "prop": "imageinfo",
                                    "format": "json", "iiprop": "url|extmetadata|size|mime", "iiurlwidth": 1280})
        d = get("https://commons.wikimedia.org/w/api.php?" + q)["query"]
        norm = {n["to"]: n["from"] for n in d.get("normalized", [])}
        for pg in d["pages"].values():
            if "imageinfo" in pg:
                out[pg["title"]] = pg["imageinfo"][0]
                if pg["title"] in norm:
                    out[norm[pg["title"]]] = pg["imageinfo"][0]
    return out


def shrink(b, edge=1600):
    """Keep the reference under ~1600 px; the original's bytes are not needed for a restyle."""
    from PIL import Image
    im = Image.open(io.BytesIO(b))
    if max(im.size) <= edge and im.format in ("JPEG", "PNG"):
        return b
    im = im.convert("RGB"); im.thumbnail((edge, edge), Image.LANCZOS)
    out = io.BytesIO(); im.save(out, "JPEG", quality=92)
    return out.getvalue()


STD_WIDTHS = (1280, 960, 500, 330, 250)   # Wikimedia serves only these to bots; other sizes and originals get a hard 429


def standard_thumb(title, info):
    w = next((x for x in STD_WIDTHS if x <= info.get("width", 0)), 250)
    if info.get("thumburl") and info.get("thumbwidth") == w:
        return info["thumburl"]
    q = urllib.parse.urlencode({"action": "query", "titles": title, "prop": "imageinfo", "format": "json",
                                "iiprop": "url", "iiurlwidth": w})
    page = next(iter(get("https://commons.wikimedia.org/w/api.php?" + q)["query"]["pages"].values()))
    return page["imageinfo"][0]["thumburl"]


def cmd_refs(ids):
    import time
    ids = [i for i in (ids or BY_ID) if not (CACHE / i / "source" / "source.json").exists()]
    files = commons_files(ids)
    infos = commons_info(files.values())
    for pid in ids:
        src = CACHE / pid / "source"
        src.mkdir(parents=True, exist_ok=True)
        fname = files.get(pid)
        if not fname:
            (src / "source.json").write_text(json.dumps({"id": pid, "reference": None,
                "reason": "no surviving likeness found (no Wikidata P18, no override)", "checked": now()}, indent=1))
            print(pid, "no likeness"); continue
        title = "File:" + fname.replace("_", " ")
        info = infos.get(title)
        if not info:
            print(pid, "Commons has no file", title); continue
        md = {k: strip_html(v.get("value")) for k, v in info.get("extmetadata", {}).items()}
        lic = (md.get("LicenseShortName") or md.get("License") or "").lower()
        img = shrink(get(standard_thumb(title, info), binary=True))
        time.sleep(1.5)
        ext = ".png" if img[:4] == b"\x89PNG" else ".jpg"
        (src / ("reference" + ext)).write_bytes(img)
        meta = {"id": pid, "name": BY_ID[pid]["name"], "file": title, "page": info["descriptionurl"],
                "original": info["url"], "downloaded": info.get("thumburl") or info["url"], "original_sha256": None,
                "author": md.get("Artist"), "date": md.get("DateTimeOriginal"), "credit": md.get("Credit"),
                "licence": md.get("LicenseShortName"), "licence_url": md.get("LicenseUrl"),
                "attribution_required": md.get("AttributionRequired"), "description": md.get("ImageDescription", "")[:600],
                "licence_ok": any(t in lic for t in OK_LICENCES) or lic.startswith("cc by"),
                "local": "reference" + ext, "sha256": sha256(img), "checked": now()}
        (src / "source.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
        print(pid, meta["licence"], "|", meta["author"], "|", meta["date"], "|", title)


def reference(pid):
    sj = CACHE / pid / "source" / "source.json"
    if not sj.exists():
        return None, None
    s = json.loads(sj.read_text())
    if not s.get("reference", True) or not s.get("local") or not s.get("licence_ok"):
        return s, None
    return s, (CACHE / pid / "source" / s["local"]).read_bytes()


# ---------------------------------------------------------------- prompts

LOOK = ("Head-and-shoulders portrait, vertical 4:5 framing, the face about a third of the frame height, "
        "centred, shoulders cut by the lower edge. Finish: a quiet, realistic painted study in oils, muted natural "
        "colour, soft light from the upper left, gentle shadow. Background: plain warm mid-grey that darkens softly "
        "toward the edges, with nothing else in it. No text, no frame, no border, no signature, no watermark, "
        "no crown, jewellery or insignia unless the reference shows it.")
DIGNITY = ("This is a respectful historical likeness. Keep the face's proportions exactly as in the reference: "
           "do not exaggerate, idealise, glamorise, modernise or caricature any feature. Natural eyes, closed or "
           "natural mouth, no visible hands.")


def prompt_for(p, src, retry_note=None):
    era = f"{p['name']} ({p['born']}-{p['died']})"
    if src and src.get("local"):
        who = (f"Repaint the person in the attached reference image, {era}, as a new portrait. "
               f"The face must follow the reference faithfully: same face shape, features, hair, age and expression. "
               f"Keep the clothing of the reference, simplified to what a head-and-shoulders crop shows.")
    else:
        who = (f"Imagine a portrait of {era}, of whom no likeness survives. Show a plausible, unremarkable person "
               f"of the right age, sex and rank, in dress correct for {p['house']} around {p['died'] - 10}. "
               f"Note: {p['note'][:300]}")
    parts = [who, LOOK, DIGNITY]
    if retry_note:
        parts.append("Correct this from the previous attempt: " + retry_note)
    return "\n\n".join(parts)


# ---------------------------------------------------------------- gemini

def gemini(prompt, ref_bytes):
    keys = [os.environ[k] for k in ("GEMINI_API_KEY2", "GEMINI_API_KEY") if os.environ.get(k)]
    parts = []
    if ref_bytes:
        mime = "image/png" if ref_bytes[:4] == b"\x89PNG" else "image/jpeg"
        parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(ref_bytes).decode()}})
    parts.append({"text": prompt})
    body = json.dumps({"contents": [{"role": "user", "parts": parts}],
                       "generationConfig": {"responseModalities": ["IMAGE"],
                                            "imageConfig": {"aspectRatio": "4:5", "imageSize": "1K"}}}).encode()
    last = None
    for key in keys:
        req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
                                     data=body, headers={"x-goog-api-key": key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                resp = json.load(r)
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code in (401, 403):
                continue   # try the next key; a key that cannot call is not a spent request
            raise RuntimeError(last)
        for c in resp.get("candidates", []):
            for part in c.get("content", {}).get("parts", []):
                d = part.get("inline_data") or part.get("inlineData")
                if d:
                    return base64.b64decode(d["data"]), resp.get("usageMetadata")
        raise RuntimeError("no image in response: " + json.dumps(resp)[:400])
    raise RuntimeError(last or "no usable Gemini key")


def cmd_gen(ids, redo=None, dry=False, allow_living=False):
    ids = [redo] if redo else (ids or list(BY_ID))
    for pid in ids:
        p = BY_ID[pid]
        if not allow_living and not possibly_dead(p):
            print(pid, "possibly living: never sent to Gemini"); continue
        have = versions(pid)
        if have and not redo:
            print(pid, f"cached v{have[-1]}: skipped"); continue
        calls = log_lines()
        if len(calls) >= BUDGET:
            sys.exit(f"budget: requests.jsonl already holds {len(calls)} calls (cap {BUDGET})")
        mine = [c for c in calls if c["id"] == pid]
        if len(mine) >= PER_PERSON:
            print(pid, f"already requested {len(mine)} times: refused"); continue
        src, ref = reference(pid)
        if src is None:
            print(pid, "no source.json yet (run refs first): skipped"); continue
        retry_note = None
        if have:
            prev = json.loads((CACHE / pid / f"v{have[-1]}" / "meta.json").read_text())
            retry_note = (prev.get("review") or {}).get("notes")
        prompt = prompt_for(p, src if ref else None, retry_note)
        ver = f"v{(have[-1] + 1) if have else 1}"
        if dry:
            print(pid, ver, "would call", MODEL, "ref" if ref else "no-ref"); print(prompt); continue
        entry = {"time": now(), "id": pid, "version": ver, "model": MODEL, "prompt_sha256": sha256(prompt.encode()),
                 "reference_sha256": sha256(ref) if ref else None, "outcome": "pending"}
        try:
            img, usage = gemini(prompt, ref)
            entry["outcome"] = "ok"
        except Exception as e:
            entry["outcome"] = "error: " + str(e)[:200]
            img = None
        with LOG.open("a") as f:
            f.write(json.dumps(entry) + "\n")
        if img is None:
            print(pid, entry["outcome"]); continue
        out = CACHE / pid / ver
        out.mkdir(parents=True, exist_ok=True)
        (out / "portrait.png").write_bytes(img)
        meta = {"id": pid, "name": p["name"], "version": ver, "model": MODEL, "prompt": prompt,
                "prompt_sha256": entry["prompt_sha256"], "reference": src if ref else None,
                "created": entry["time"], "sha256": sha256(img), "label": label(p, src if ref else None),
                "imagined": ref is None, "review": None, "usage": usage}
        (out / "meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
        print(pid, ver, "written", len(img), "bytes")


def possibly_dead(p):
    """Default guard: no portraits of possibly living people (--allow-living only on HagopJay's explicit say). Require a recorded death year, and a birth over 110 years ago."""
    year = datetime.date.today().year
    return bool(p.get("died")) and int(p["died"]) <= year and bool(p.get("born")) and year - int(p["born"]) > 110


def label(p, src):
    if not src:
        return "AI-imagined portrait: no likeness survives"
    who = (src.get("author") or "unknown artist").split("\n")[0].strip()
    who = re.sub(r"\s+", " ", who)[:80]
    yr = re.search(r"1[0-9]{3}", src.get("date") or "")
    lic = "public domain" if any(t in (src.get("licence") or "").lower() for t in OK_LICENCES) else src.get("licence")
    return f"AI portrait after {who}{', ' + yr.group(0) if yr else ''} ({lic})"


def cmd_review(pid, verdict, notes, version=None):
    v = version or f"v{versions(pid)[-1]}"
    mp = CACHE / pid / v / "meta.json"
    meta = json.loads(mp.read_text())
    meta["review"] = {"verdict": verdict, "notes": notes, "reviewed": now(),
                      "checks": ["likeness", "dignity", "hands-eyes-teeth", "era dress", "clean background"]}
    mp.write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    print(pid, v, verdict)


# ---------------------------------------------------------------- post-processing

def initials(name):
    if " of " in name or "Emperor" in name:      # a monarch goes by the first name alone
        return name[0]
    name = re.sub(r"\(.*?\)|'.*?'|,.*$", "", name)
    words = [w for w in name.split() if w[0].isupper() and w not in ("I", "II", "IV", "Of")]
    return (words[0][0] + (words[-1][0] if len(words) > 1 else "")).upper()


def font(size):
    from PIL import ImageFont
    for f in ("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def oval_mask(w, h, feather):
    from PIL import Image, ImageDraw, ImageFilter
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).ellipse([feather, feather * 0.7, w - feather, h - feather * 0.4], fill=255)
    return m.filter(ImageFilter.GaussianBlur(feather / 2.2))


def cutout(img, size=768):
    from PIL import Image
    w = size; h = int(size * 5 / 4)
    im = img.convert("RGB").resize((w, h), Image.LANCZOS)
    rgba = im.convert("RGBA")
    rgba.putalpha(oval_mask(w, h, size * 0.09))
    return rgba


def monogram(p, size=768):
    from PIL import Image, ImageDraw
    w = size; h = int(size * 5 / 4)
    fam = p["family"] if p["family"] != "darwin_wedgwood" else ("darwin" if "Darwin" in p["name"] else "wedgwood")
    col = FAMILY_COLOR.get(fam, "#555555")
    im = Image.new("RGBA", (w, h), col)
    d = ImageDraw.Draw(im)
    t = initials(p["name"])
    f = font(int(size * 0.32))
    bb = d.textbbox((0, 0), t, font=f)
    d.text(((w - bb[2] - bb[0]) / 2, (h - bb[3] - bb[1]) / 2), t, font=f, fill=(245, 240, 230, 235))
    im.putalpha(oval_mask(w, h, size * 0.09))
    return im


def best(pid):
    """Latest version that passed review; else None."""
    for v in reversed(versions(pid)):
        m = json.loads((CACHE / pid / f"v{v}" / "meta.json").read_text())
        if (m.get("review") or {}).get("verdict") == "pass":
            return f"v{v}", m
    return None, None


def cmd_post():
    from PIL import Image
    calls = log_lines()
    fixed = json.loads((ROOT / "labels.json").read_text()) if (ROOT / "labels.json").exists() else {}   # hand-cleaned labels
    people = []
    for p in PEOPLE:
        pid = p["id"]
        v, meta = best(pid)
        src = reference(pid)[0]
        entry = {"id": pid, "name": p["name"], "family": p["family"], "born": p["born"], "died": p["died"],
                 "requests": sum(1 for c in calls if c["id"] == pid)}
        if v:
            d = CACHE / pid / v
            img = Image.open(d / "portrait.png")
            cutout(img).save(d / "cutout-768.webp", quality=88, method=6)
            t = img.convert("RGB"); t.thumbnail((256, 320), Image.LANCZOS); t.save(d / "thumb-256.webp", quality=85)
            entry.update(status="ok", version=v, label=fixed.get(pid, meta["label"]), imagined=meta["imagined"],
                         portrait=f"cache/{pid}/{v}/portrait.png", cutout=f"cache/{pid}/{v}/cutout-768.webp",
                         thumb=f"cache/{pid}/{v}/thumb-256.webp", review=meta["review"]["notes"],
                         source=(src or {}).get("page"), source_author=(src or {}).get("author"),
                         source_licence=(src or {}).get("licence"))
        else:
            d = CACHE / pid / "monogram"
            d.mkdir(parents=True, exist_ok=True)
            mono = monogram(p); mono.save(d / "cutout-768.webp", quality=90)
            t = mono.copy(); t.thumbnail((256, 320)); t.save(d / "thumb-256.webp", quality=90)
            status = "rejected" if versions(pid) else "pending"
            entry.update(status=status, label="Monogram card: no AI portrait", imagined=None,
                         cutout=f"cache/{pid}/monogram/cutout-768.webp", thumb=f"cache/{pid}/monogram/thumb-256.webp")
        people.append(entry)
    man = {"version": 1, "generated": now(), "model": MODEL, "budget": BUDGET, "calls": len(calls),
           "rule": "Cache-first: never re-request a cached person. Every image is AI-made and labelled.",
           "people": people}
    (ROOT / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False))
    contact(people)
    print("manifest:", sum(e["status"] == "ok" for e in people), "ok,",
          sum(e["status"] == "rejected" for e in people), "rejected,", sum(e["status"] == "pending" for e in people), "pending;",
          len(calls), "calls")


def contact(people):
    from PIL import Image, ImageDraw
    cw, ch, cols, pad, lab = 220, 275, 7, 18, 46
    rows = (len(people) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (cw + pad) + pad, rows * (ch + lab + pad) + pad), (128, 128, 128))
    d = ImageDraw.Draw(sheet)
    f = font(13)
    for i, e in enumerate(people):
        x = pad + (i % cols) * (cw + pad); y = pad + (i // cols) * (ch + lab + pad)
        c = Image.open(ROOT / e["cutout"]).convert("RGBA").resize((cw, ch), Image.LANCZOS)
        sheet.paste(c, (x, y), c)
        nm = re.sub(r"\s*\(.*?\)", "", e["name"])[:30]
        d.text((x, y + ch + 4), nm, font=f, fill=(20, 20, 20))
        d.text((x, y + ch + 21), f"{e['born']}-{e['died']} · {e['status']}", font=f, fill=(45, 45, 45))
    sheet.save(ROOT / "contact-v1.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("refs"); a.add_argument("ids", nargs="*")
    a = sp.add_parser("gen"); a.add_argument("ids", nargs="*"); a.add_argument("--redo"); a.add_argument("--dry-run", action="store_true"); a.add_argument("--allow-living", action="store_true")
    a = sp.add_parser("review"); a.add_argument("id"); a.add_argument("--verdict", choices=["pass", "fail"], required=True)
    a.add_argument("--notes", required=True); a.add_argument("--version")
    sp.add_parser("post")
    x = ap.parse_args()
    if x.cmd == "refs": cmd_refs(x.ids)
    elif x.cmd == "gen": cmd_gen(x.ids, x.redo, x.dry_run, x.allow_living)
    elif x.cmd == "review": cmd_review(x.id, x.verdict, x.notes, x.version)
    elif x.cmd == "post": cmd_post()
