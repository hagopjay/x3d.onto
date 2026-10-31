// sky.glsl (style board): the backdrop, computed per pixel from the view direction; display sRGB out (a designed ground, not a light source).
// A vertical sweep from S_GROUND_BOT to S_GROUND_TOP, a soft pool of light behind the opening view, optional large-scale mottling (paper or
// smoke) and, for the dark direction only, a sparse layer of dim hashed stars. Nothing is fetched. d: unit direction; q: tier; pxa: pixel footprint.
vec3 skyCol(vec3 d, int q, float T, float pxa, float seed) {
  vec3 sd = vec3(seed * 17.31, seed * 5.77, seed * 11.13);
  vec3 col = mix(S_GROUND_BOT, S_GROUND_TOP, smoothstep(-.75, .35, d.y));
  float ang = acos(clamp(dot(d, S_POOL_DIR), -1., 1.));
  col = mix(col, S_POOL, S_POOL_K * exp(-ang * ang / (S_POOL_W * S_POOL_W)));
  if (S_MOTTLE > 0.) col *= 1. + S_MOTTLE * (fbm(d * 2.4 + sd, 2 + q) - .5) * 2.;
  if (S_STARS > 0.) {
    for (int L = 0; L < 2; L++) {
      if (L > q) break;
      float sc = L == 0 ? 60. : 150.;
      if (pxa * sc > .5) break;
      vec3 g = d * sc + sd * float(L + 1), id = floor(g), f = fract(g) - .5;
      float hh = h13(id);
      if (hh < .975) continue;
      vec3 jit = (vec3(h13(id + 7.), h13(id + 11.), h13(id + 13.)) - .5) * .5;
      float r = length(f - jit), rad = max(.06, 1.2 * pxa * sc), e = (.06 / rad) * (.06 / rad);
      col += vec3(.95, .9, .82) * smoothstep(rad, 0., r) * e * S_STARS * (.5 + 2. * pow(h13(id + 3.), 4.));
    }
  }
  return col;
}
