#!/usr/bin/env python3
"""Make engine/common.js from the shared PolyXandria engine of Gobbler 3 Deep (x3d.ML branch claude/project-thread-0105va @ 51e185f,
gobbler-v3/deep/build-private/common.js) plus two small changes. Added: PX.tourHold() / PX.tourRelease(), a pause that keeps the tour's phase so the
camera resumes where it stopped instead of restarting the spiral; hover uses it so the star under the pointer holds still. Removed: the v3
H-key toggle of the clean mode, because H is now a momentary UI none. Nothing else in the file changes. Every edit is asserted to match exactly once and the input hash is checked.

    python3 -I gobbler-v4/tools/patch_engine.py data/deep/common.js gobbler-v4/engine/common.js
"""
import hashlib, sys

SRC_SHA256_PREFIX = 'a3112205c7cb0a1694d0'   # sha256 of the unpatched file, first 20 hex digits


def once(s, old, new):
    if s.count(old) != 1:
        raise SystemExit('patch anchor not found exactly once: %r (found %d)' % (old[:60], s.count(old)))
    return s.replace(old, new)


def main(src, dst):
    raw = open(src, 'rb').read()
    h = hashlib.sha256(raw).hexdigest()
    if not h.startswith(SRC_SHA256_PREFIX):
        raise SystemExit('unexpected common.js (sha256 %s...), refusing to patch' % h[:20])
    s = raw.decode('utf-8')
    s = once(s, "  var tourVp = null, tourT0 = 0, tourRaf = 0;\n",
             "  var tourVp = null, tourT0 = 0, tourRaf = 0, tourHeld = false, tourHeldAt = 0;   /* v4: tourHeld = paused by hover, tourHeldAt = elapsed ms at the pause */\n")
    s = once(s, "    PX.tourOn = true; tourT0 = performance.now(); cancelAnimationFrame(tourRaf); tourRaf = requestAnimationFrame(tourStep);\n",
             "    PX.tourOn = true; tourHeld = false; tourT0 = performance.now(); cancelAnimationFrame(tourRaf); tourRaf = requestAnimationFrame(tourStep);\n")
    s = once(s, "    PX.tourOn = false; cancelAnimationFrame(tourRaf);\n    var b = $('#btn-tour'); if (b) { b.classList.remove('on'); b.textContent = 'Resume tour'; }\n  }\n  PX.tourStart = tourStart; PX.tourStop = tourStop;\n",
             "    PX.tourOn = false; tourHeld = false; cancelAnimationFrame(tourRaf);\n    var b = $('#btn-tour'); if (b) { b.classList.remove('on'); b.textContent = 'Resume tour'; }\n  }\n"
             "  /* v4: pause the tour without losing its phase (the button keeps saying \"Pause tour\"); a later tourStop() or tourStart() cancels the hold */\n"
             "  function tourHold() { if (!PX.tourOn) return false; tourHeldAt = performance.now() - tourT0; tourHeld = true; PX.tourOn = false; cancelAnimationFrame(tourRaf); return true; }\n"
             "  function tourRelease() { if (!tourHeld) return false; tourHeld = false; PX.tourOn = true; tourT0 = performance.now() - tourHeldAt; cancelAnimationFrame(tourRaf); tourRaf = requestAnimationFrame(tourStep); return true; }\n"
             "  PX.tourStart = tourStart; PX.tourStop = tourStop; PX.tourHold = tourHold; PX.tourRelease = tourRelease; PX.tourHeld = function () { return tourHeld; };\n")
    s = once(s, "    el.addEventListener('pointerdown', function () { if (PX.tourOn) tourStop(); });\n",
             "    el.addEventListener('pointerdown', function () { if (PX.tourOn || tourHeld) tourStop(); });\n")
    s = once(s, "    document.addEventListener('keydown', function (ev) { if (ev.key === 'h' && !ev.metaKey && !ev.ctrlKey) clean(!$('#stage').classList.contains('clean')); });\n",
             "    /* v4: the H key belongs to the overlay (hold = momentary UI none), so the v3 toggle is gone */\n")
    s = "/* v4 engine: the Gobbler 3 Deep common.js plus PX.tourHold/tourRelease (see gobbler-v4/tools/patch_engine.py). */\n" + s
    open(dst, 'w').write(s)
    print('wrote %s (%d bytes) from %s' % (dst, len(s), h[:12]))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
