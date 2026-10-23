"""Shared report shape and a tiny hash-chain 'tether' for the cross-domain validator prototypes.
Mirrors the roles x3d_mcp plays for X3D: located diagnostics with a rung (the verification ladder), a fix hint, and a record that can be verified later.
The chain here is a SKETCH in the spirit of x3dprov, not x3dprov itself (no signing, no x3d.ML code)."""
import hashlib, json, time
from dataclasses import dataclass, asdict, field

RUNGS = {0: "parses", 1: "typed", 2: "valid", 3: "coherent", 4: "lawful", 5: "visible", 6: "complete", 7: "meaningful"}

@dataclass
class Diag:
    rule: str; severity: str; rung: int; where: str; message: str; fix: str = ""; x3d_counterpart: str = ""

@dataclass
class Report:
    domain: str; oracle: str; diags: list = field(default_factory=list); ms: float = 0.0
    @property
    def errors(self): return [d for d in self.diags if d.severity == "error"]
    @property
    def valid(self): return not self.errors
    def to_json(self): return {"domain": self.domain, "oracle": self.oracle, "valid": self.valid, "errors": len(self.errors),
                               "warnings": sum(d.severity == "warning" for d in self.diags), "infos": sum(d.severity == "info" for d in self.diags),
                               "ms": round(self.ms, 2), "diagnostics": [asdict(d) for d in self.diags]}

def sha(x): return hashlib.sha256(x if isinstance(x, bytes) else x.encode()).hexdigest()

def stamp(chain, op, artifact, report_json):
    """Append a step: op, artifact hash, report hash, previous step hash."""
    prev = chain[-1]["h"] if chain else "0" * 64
    step = {"op": op, "artifact": sha(artifact)[:16], "report": sha(json.dumps(report_json, sort_keys=True))[:16], "prev": prev[:16], "t": round(time.time())}
    step["h"] = sha(json.dumps(step, sort_keys=True))
    return chain + [step]

def verify(chain, artifact=None):
    """ok / stale (artifact changed after the last step) / broken-chain (a step was edited or removed)."""
    prev = "0" * 64
    for s in chain:
        body = {k: v for k, v in s.items() if k != "h"}
        if s["prev"] != prev[:16] or sha(json.dumps(body, sort_keys=True)) != s["h"]: return "broken-chain"
        prev = s["h"]
    if artifact is not None and chain and chain[-1]["artifact"] != sha(artifact)[:16]: return "stale"
    return "ok"
