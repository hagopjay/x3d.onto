#!/usr/bin/env python3
"""Drop-in for shroud-artifacts/tools/vertex.py that uses a Gemini API key (GEMINI_API_KEY, generativelanguage.googleapis.com) instead of Vertex.
Same call(model, parts, ...) -> dict(text, est_usd, tokens_in, tokens_out, finish) and spent(). A part is a str (text) or bytes/Path (an image).
Every call appends one row to the shared ledger (GEMINI_LEDGER, default /mnt/project-files/x3d-loom/gemini-ledger.jsonl); a hard cap
(GEMINI_CAP_USD, default 100) is checked against the ledger before each call, and crossing a multiple of $25 prints an ALERT line.
Prices are the same upper-bound ASSUMPTIONS as vertex.py (flash 0.75 / 3.75 per 1M in / out, pro 2.5 / 15, thinking billed as output), not a billing export.
usage: python3 gemini_api.py ping [MODEL] | python3 gemini_api.py spent"""
import base64, json, mimetypes, os, sys, threading, time, urllib.error, urllib.request
from pathlib import Path
API = "https://generativelanguage.googleapis.com/v1beta/models"
LEDGER = Path(os.environ.get("GEMINI_LEDGER", "/mnt/project-files/x3d-loom/gemini-ledger.jsonl"))
CAP = float(os.environ.get("GEMINI_CAP_USD", "100"))
ALERT_EVERY = 25.0
PRICE = {"flash": (0.75, 3.75), "pro": (2.5, 15.0)}
_lock = threading.Lock()
def price(model): return PRICE["pro" if "pro" in model else "flash"]
def spent():
    if not LEDGER.exists(): return 0.0
    return sum(json.loads(l).get("est_usd", 0) for l in LEDGER.read_text().splitlines() if l.strip())
def _part(p):
    if isinstance(p, str): return {"text": p}
    if isinstance(p, Path): data, mime = p.read_bytes(), mimetypes.guess_type(p.name)[0] or "image/png"
    else: data, mime = p, "image/png"
    return {"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}}
def call(model, parts, location=None, max_tokens=8192, temperature=1.0, json_out=False, purpose="", thinking=None):
    """location is accepted and ignored (the API key endpoint is global)."""
    key = os.environ.get("GEMINI_API_KEY") or sys.exit("GEMINI_API_KEY is not set")
    before = spent()
    if before >= CAP: raise RuntimeError(f"gemini ledger cap reached: ${before:.2f} >= ${CAP:.2f}")
    cfg = {"maxOutputTokens": max_tokens, "temperature": temperature}
    if json_out: cfg["responseMimeType"] = "application/json"
    if thinking is not None: cfg["thinkingConfig"] = {"thinkingBudget": thinking}
    body = json.dumps({"contents": [{"role": "user", "parts": [_part(p) for p in parts]}], "generationConfig": cfg}).encode()
    req = urllib.request.Request(f"{API}/{model}:generateContent", body, {"content-type": "application/json", "x-goog-api-key": key})
    t0 = time.time()
    for attempt in range(5):   # transient failures (connection reset, 429, 5xx) are retried with backoff; a 4xx is not
        try:
            with urllib.request.urlopen(req, timeout=400) as r: d = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == 4: raise
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if attempt == 4: raise
        time.sleep(2 ** (attempt + 1))
    u = d.get("usageMetadata", {}); tin = u.get("promptTokenCount", 0); tout = u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)
    pi, po = price(model); usd = (tin * pi + tout * po) / 1e6
    c = (d.get("candidates") or [{}])[0]; text = "".join(p.get("text", "") for p in c.get("content", {}).get("parts", []) if not p.get("thought"))
    row = dict(t=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), model=model, purpose=purpose, tokens_in=tin, tokens_out=tout, est_usd=round(usd, 6), seconds=round(time.time() - t0, 1), finish=c.get("finishReason"))
    with _lock:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with open(LEDGER, "a") as f: f.write(json.dumps(row) + "\n")
        after = before + usd
        if int(after // ALERT_EVERY) > int(before // ALERT_EVERY): print(f"ALERT gemini spend crossed ${ALERT_EVERY * int(after // ALERT_EVERY):.0f} (ledger ${after:.2f})", file=sys.stderr, flush=True)
    if c.get("finishReason") not in ("STOP", "MAX_TOKENS") and not text: raise RuntimeError(f"no text, finish={c.get('finishReason')} feedback={d.get('promptFeedback')}")
    return dict(text=text, est_usd=usd, tokens_in=tin, tokens_out=tout, finish=c.get("finishReason"))
if __name__ == "__main__":
    if sys.argv[1:2] == ["spent"]: print(f"${spent():.4f} in {LEDGER}")
    else:
        m = sys.argv[2] if len(sys.argv) > 2 else "gemini-2.5-flash"
        try: print(call(m, ["Reply with the single word OK."], max_tokens=200, purpose="ping"))
        except urllib.error.HTTPError as e: print(e.code, e.read().decode()[:400])
