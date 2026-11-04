# FACTS entry (flywheel stage 2)

One entry per trap, appended as a dated section to the project's or x3d.onto's FACTS.md. Grade moves are appended with their reason, never edited in place.

```
### <id> · <short title> · <date>
- Symptom: <what was seen, where>
- Instrument: <tool, version, commit, renderer>
- Cause: <as far as isolated>; grade <C/L/S>
- Fix: <generator or card change, commit>
- Test: passing fixture <path, sha256>; failing fixture <path, sha256>; expected diagnostic <CODE>
- Scope: <runtime / version / profile it applies to; what it does not establish>
- Rule: <gate rule id, or "proposed">; corpus re-run: <files, hits before/after>
- Upstream: <no | proposed, held for "send">
```
