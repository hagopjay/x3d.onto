/* Corner placement for the hover card (Gobbler v4 cornerstone UI).
 * Pure function, no DOM: the same code runs in the mock, in node tests and, later, in the live viewer.
 * Inputs are screen-space only, so there is nothing to add to the X3D scene (no per-star sensors).
 *   W,H        viewport size in px
 *   hover      {x,y} screen position of the hovered star
 *   size       {w,h} card size in px
 *   density    function (x,y) -> 0..1, how much "subject" is at a screen point
 *              (the mock reads it from the still's pixels; the live viewer builds it from projected star and edge counts)
 *   margin     distance from the viewport edge (matches the viewer's 22 px stage padding)
 *   reserved   per-corner height already used by always-on chips, so a card never covers them
 *   halo       radius around the hovered star that no card may cover
 *   prev       the slot used last time (hysteresis: the card does not jump while the mouse drifts)
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory(); else root.Place = factory();
})(this, function () {
  'use strict';
  var SLOTS = ['TL', 'TR', 'BL', 'BR'];
  var WEIGHT = { density: 2.0, leader: 0.6, dist: 0.35 };
  var KEEP_MARGIN = 0.12;      /* keep the previous slot unless another beats it by more than this */
  var NARROW = 720;            /* below this width the card becomes a bottom sheet */

  function slotRect(slot, W, H, size, m, reserved) {
    var r = (reserved && reserved[slot]) || { h: 0 };
    return {
      x: slot.charAt(1) === 'L' ? m : W - m - size.w,
      y: slot.charAt(0) === 'T' ? m + r.h : H - m - r.h - size.h,
      w: size.w, h: size.h
    };
  }
  function circleHitsRect(c, r) {
    var nx = Math.max(r.x, Math.min(c.x, r.x + r.w)), ny = Math.max(r.y, Math.min(c.y, r.y + r.h));
    var dx = c.x - nx, dy = c.y - ny; return dx * dx + dy * dy < c.r * c.r;
  }
  function inside(r, W, H) { return r.x >= 0 && r.y >= 0 && r.x + r.w <= W && r.y + r.h <= H; }
  function meanDensity(r, density, n) {
    var s = 0, c = 0, i, j; n = n || 8;
    for (i = 0; i < n; i++) for (j = 0; j < n; j++) { s += density(r.x + (i + 0.5) * r.w / n, r.y + (j + 0.5) * r.h / n); c++; }
    return s / c;
  }
  /* the leader line runs from the hovered star to the nearest point of the card */
  function nearestOnRect(p, r) { return { x: Math.max(r.x, Math.min(p.x, r.x + r.w)), y: Math.max(r.y, Math.min(p.y, r.y + r.h)) }; }
  function leaderDensity(p, r, density) {
    var q = nearestOnRect(p, r), s = 0, n = 24, i;
    for (i = 1; i < n; i++) s += density(p.x + (q.x - p.x) * i / n, p.y + (q.y - p.y) * i / n);
    return s / (n - 1);
  }

  function choose(o) {
    var W = o.W, H = o.H, size = o.size, m = o.margin == null ? 22 : o.margin, halo = o.halo == null ? 96 : o.halo;
    if (W < NARROW) return { slot: 'SHEET', rect: { x: 0, y: Math.max(0, H - size.h - m), w: W, h: Math.min(size.h, H * 0.5) }, scores: [], kept: false };
    var diag = Math.hypot(W, H), circle = { x: o.hover.x, y: o.hover.y, r: halo }, scores = [], best = null, prevScore = null, k;
    for (k = 0; k < SLOTS.length; k++) {
      var s = SLOTS[k], r = slotRect(s, W, H, size, m, o.reserved), c = r.x + r.w / 2, d = r.y + r.h / 2;
      var feasible = inside(r, W, H) && !circleHitsRect(circle, r);
      var den = meanDensity(r, o.density), led = leaderDensity(o.hover, r, o.density);
      var dist = Math.hypot(c - o.hover.x, d - o.hover.y) / diag;
      var score = WEIGHT.density * den + WEIGHT.leader * led + WEIGHT.dist * dist + (feasible ? 0 : 10);
      var row = { slot: s, rect: r, feasible: feasible, density: den, leader: led, dist: dist, score: score };
      scores.push(row);
      if (feasible && (!best || score < best.score)) best = row;
      if (o.prev === s && feasible) prevScore = row;
    }
    var kept = false;
    if (prevScore && best && prevScore.score - best.score <= KEEP_MARGIN) { best = prevScore; kept = true; }
    if (!best) {              /* nothing fits: dock to the corner farthest from the star, shrunk to a strip */
      var far = scores.slice().sort(function (a, b) {
        return Math.hypot(b.rect.x - o.hover.x, b.rect.y - o.hover.y) - Math.hypot(a.rect.x - o.hover.x, a.rect.y - o.hover.y);
      })[0];
      best = far; kept = false;
    }
    return { slot: best.slot, rect: best.rect, scores: scores, kept: kept, leader: nearestOnRect(o.hover, best.rect) };
  }

  return { choose: choose, slotRect: slotRect, meanDensity: meanDensity, WEIGHT: WEIGHT, SLOTS: SLOTS, NARROW: NARROW, KEEP_MARGIN: KEEP_MARGIN };
});
