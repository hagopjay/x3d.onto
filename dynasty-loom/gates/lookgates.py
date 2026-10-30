"""LOOK gates that need only a frame and the scene's own numbers (no model): non-black, node recall, label overlap, label contrast.

  python3 -I lookgates.py FRAME.jpg [...]      prints the non-black verdict per frame

nonblack()     replaces the JPEG-size proxy (frames.js retakes under 90 KB, e2e.js passes over 80 KB) with pixel statistics.
               A frame is black when its 99th-percentile luma is under 0.25, or under 2% of its pixels have luma > 0.1;
               With a golden frame for the same stop both rules become relative: a quarter of its lit share and half its 99.9th-percentile
               luma (a sparse family starfield can be lit on under 2% of its pixels and still be right).
node_recall()  of the people the data says are on screen at this stop (projected with the stop's camera), the share whose
               pixel neighbourhood is lit: catches a stalled Inline, a culled branch or a wrong camera that a judge would score anyway.
label_metrics() overlap between label boxes, smallest text height, labels off screen.
contrast()     WCAG contrast of a label's text colour against the frame pixels behind it (median)."""
import sys

import numpy as np
from PIL import Image

LIT, MIN_LIT_SHARE, MIN_P99, GOLDEN_SHARE = 0.10, 0.02, 0.25, 0.25


def luma(a):
    a = np.asarray(a, dtype=np.float32) / 255.0
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def load(path):
    return np.asarray(Image.open(path).convert('RGB'))


def frame_stats(img):
    y = luma(img)
    return dict(mean=float(y.mean()), p99=float(np.percentile(y, 99)), p999=float(np.percentile(y, 99.9)), lit=float((y > LIT).mean()), std=float(y.std()), w=int(y.shape[1]), h=int(y.shape[0]))


def nonblack(img, golden=None):
    s = frame_stats(img); why = []
    if golden is None and s['lit'] < MIN_LIT_SHARE: why.append('lit share %.4f < %.2f' % (s['lit'], MIN_LIT_SHARE))
    if golden is not None and s['lit'] < GOLDEN_SHARE * golden['lit']: why.append('lit share %.4f < %.2f x golden %.4f' % (s['lit'], GOLDEN_SHARE, golden['lit']))
    if golden is None and s['p99'] < MIN_P99: why.append('p99 luma %.3f < %.2f' % (s['p99'], MIN_P99))
    if golden is not None and s['p999'] < 0.5 * golden['p999']: why.append('p99.9 luma %.3f < half the golden %.3f' % (s['p999'], golden['p999']))
    return dict(s, ok=not why, why=why)


def node_recall(img, pts, radius=3, thr=0.15):
    """pts: [(id, x, y)] in pixels, projected from the data with the stop's camera. Returns recall and the ids not seen."""
    y = luma(img); h, w = y.shape; miss = []; seen = 0; onscreen = 0
    for pid, px, py in pts:
        if not (0 <= px < w and 0 <= py < h): continue
        onscreen += 1
        x0, x1, y0, y1 = max(0, int(px) - radius), min(w, int(px) + radius + 1), max(0, int(py) - radius), min(h, int(py) + radius + 1)
        if y[y0:y1, x0:x1].max() >= thr: seen += 1
        else: miss.append(pid)
    return dict(onscreen=onscreen, seen=seen, recall=(seen / onscreen) if onscreen else None, missed=miss)


def label_metrics(boxes, W, H, min_px=12):
    """boxes: [(id, x, y, w, h)] in pixels (text boxes as drawn). Overlap share = summed pairwise intersection / summed area."""
    area = sum(b[3] * b[4] for b in boxes) or 1; inter = 0.0; hit = set()
    for i, (a, ax, ay, aw, ah) in enumerate(boxes):
        for b, bx, by, bw, bh in boxes[i + 1:]:
            ix = max(0.0, min(ax + aw, bx + bw) - max(ax, bx)); iy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
            if ix * iy > 0: inter += ix * iy; hit.update((a, b))
    off = [b[0] for b in boxes if b[1] < 0 or b[2] < 0 or b[1] + b[3] > W or b[2] + b[4] > H]
    small = [b[0] for b in boxes if b[4] < min_px]
    return dict(n=len(boxes), overlap_share=inter / area, overlapping=sorted(hit), offscreen=off, too_small=small, min_height=min((b[4] for b in boxes), default=None))


def _rel(c):
    c = np.asarray(c, dtype=np.float64) / 255.0
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def contrast(img, box, text_rgb):
    """WCAG 2 contrast ratio of the text colour against the median pixel behind the box"""
    _, x, y, w, h = box; patch = img[max(0, int(y)):int(y + h), max(0, int(x)):int(x + w)].reshape(-1, 3)
    bg = np.median(patch, axis=0); l1, l2 = float(_rel(np.array(text_rgb))), float(_rel(bg))
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


if __name__ == '__main__':
    for p in sys.argv[1:]:
        r = nonblack(load(p))
        print('%-5s lit %.4f p99 %.3f mean %.3f  %s  %s' % ('ok' if r['ok'] else 'BLACK', r['lit'], r['p99'], r['mean'], p, '; '.join(r['why'])))
