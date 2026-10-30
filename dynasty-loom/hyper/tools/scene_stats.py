"""scene_stats.py FRAME.png:x0,y0,x1,y1 [...]: lookgates.py frame_stats on the scene area of a frame (the page's safe rect: no UI panels) plus the
share of clipped-white pixels (luma >= 254.5/255). With --inside it also applies the Inside lookgate of build 2 (critique fix 1):
mean <= 0.22, lit <= 0.70, clipped <= 0.3 percent. Prints one JSON line per frame; exit 1 if an Inside gate fails.
With --ab A.png@B.png:box (build 3) it compares A, a frozen frame, with B, the same frame with the threads hidden: notch is the share of the
box where the threads make a pixel darker by more than 0.05 luma AND leave it dark (luma < 0.15), a dark stroke cut across what is behind
(gate_hyper.js threadsAddLight, the notch gate); darker counts every darkened pixel, including a lit subject thread rightly hiding a
brighter ring behind it. Calibrated on the same stops: build 2 notch 0.0041 (S02) and 0.00076 (S05), build 3 0 on all 22 close frames.
With --notch (build 3, a first try, kept as a probe: it also flags sky beside bright lines, so it does not separate build 2 from build 3) it also measures dark notches: pixels darker than the local sky (see notch_share), which is what the
rest's opaque cores drew across the subject's glow and the nebula in build 2. Reported as a share of the scene area; the Notch lookgate is
notch <= NOTCH_MAX."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'gates'))
import numpy as np
from lookgates import frame_stats, load, luma
INSIDE = dict(mean=0.22, lit=0.70, clipped=0.003)
NOTCH_MAX = 0.0015


def notch_share(img, blk=16, q=35):
    """pixels darker than the local sky: the sky is the q-th percentile luma of each blk x blk block (thin threads are a small share of a
    block, so it stays the sky's level); a pixel is a notch when the block's sky is visible (> 0.06) and the pixel is under 0.6 of it"""
    y = luma(img); H, W = (y.shape[0] // blk) * blk, (y.shape[1] // blk) * blk; y = y[:H, :W]
    sky = np.percentile(y.reshape(H // blk, blk, W // blk, blk).transpose(0, 2, 1, 3).reshape(H // blk, W // blk, -1), q, axis=2)
    S = np.repeat(np.repeat(sky, blk, axis=0), blk, axis=1)
    return float(((S > 0.06) & (y < 0.6 * S)).mean())


bad = 0
args = [a for a in sys.argv[1:] if not a.startswith('--')]
if '--ab' in sys.argv:   # A@B:box: the share of the box where A is darker than B by more than 0.05 luma (B = the same frame without threads)
    for a in args:
        fs, box = a.rsplit(':', 1); fa, fb = fs.split('@'); x0, y0, x1, y1 = [int(v) for v in box.split(',')]
        ya, yb = luma(load(fa)[y0:y1, x0:x1]), luma(load(fb)[y0:y1, x0:x1]); d = yb - ya
        print(json.dumps(dict(file=os.path.basename(fa), notch=round(float(((d > 0.05) & (ya < 0.15)).mean()), 6), darker=round(float((d > 0.05).mean()), 6),
                              darker_max=round(float(d.max()), 4), brighter=round(float((d < -0.05).mean()), 4), crop=[x0, y0, x1, y1])))
    sys.exit(0)
for a in args:
    f, box = a.rsplit(':', 1); x0, y0, x1, y1 = [int(v) for v in box.split(',')]
    img = load(f)[y0:y1, x0:x1]
    s = frame_stats(img); s['clipped'] = float((luma(img) >= 254.5 / 255).mean()); s['crop'] = [x0, y0, x1, y1]
    out = dict(file=os.path.basename(f), **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in s.items()})
    if '--notch' in sys.argv:
        out['notch'] = round(notch_share(img), 5); out['notch_gate'] = 'ok' if out['notch'] <= NOTCH_MAX else 'FAIL notch %.5f > %s' % (out['notch'], NOTCH_MAX); bad += out['notch'] > NOTCH_MAX
    if '--inside' in sys.argv:
        why = [k for k in ('mean', 'lit', 'clipped') if s[k] > INSIDE[k]]
        out['inside_gate'] = 'ok' if not why else 'FAIL ' + ', '.join('%s %.4f > %s' % (k, s[k], INSIDE[k]) for k in why); bad += bool(why)
    print(json.dumps(out))
sys.exit(1 if bad else 0)
