// sky.glsl: the host sky, computed per pixel from the view direction and a seed; nothing is fetched.
// d: unit direction; q: tier (0 fast, 1 balanced, 2 ultra); T: seconds in the 600 s loop; pxa: pixel footprint in radians (0 = no star LOD)
vec3 skyCol(vec3 d, int q, float T, float pxa, float seed) {
  vec3 sd = vec3(seed * 17.31, seed * 5.77, seed * 11.13);
  vec3 gN = normalize(vec3(.28, .92, -.27));                       // the galactic plane's pole
  float gl = dot(d, gN), band = exp(-gl * gl * 7.);
  int oct = 2 + 2 * q;                                             // nebula octaves: 2, 4, 6
  vec3 p = d * 2.2 + sd;
  float w = fbm(p * 1.4 + 4.1, max(oct - 2, 1));
  float n = fbm(p + 1.8 * vec3(w, -w, w * .5), oct);               // domain-warped nebula
  float m = fbm(p * 2.3 - 3.7, max(oct - 1, 1));
  float neb = smoothstep(q == 0 ? .57 : .5, .86, n);              // fewer octaves spread wider: raise the floor so tiers match
  vec3 col = vec3(.0035, .003, .009);
  col += neb * neb * mix(vec3(.36, .05, .50), vec3(.02, .30, .42), smoothstep(.35, .65, m)) * (.06 + .2 * band);
  col += vec3(.80, .20, .32) * pow(smoothstep(.6, .95, n * (.6 + m)), 3.) * .14 * band;
  col += vec3(.10, .09, .16) * band * .07;                         // unresolved starlight along the band
  if (q > 0) col *= 1. - .6 * band * smoothstep(.5, .8, fbm(p * 4.7 + 9.3, 3));   // dust lanes
  for (int L = 0; L < 3; L++) {                                    // hashed stars, one layer per tier
    if (L > q) break;
    float sc = L == 0 ? 60. : (L == 1 ? 150. : 320.);
    if (pxa * sc > .5) break;                                      // LOD by pixel footprint: no layer finer than ~2 px per cell
    vec3 g = d * sc + sd * float(L + 1), id = floor(g), f = fract(g) - .5;
    float hh = h13(id);
    if (hh < .955 - .03 * band) continue;
    vec3 jit = (vec3(h13(id + 7.), h13(id + 11.), h13(id + 13.)) - .5) * .5;
    float r = length(f - jit);
    float rad = max(.07, 1.3 * pxa * sc);                          // a star is never thinner than ~1.3 px ...
    float e = (.07 / rad) * (.07 / rad);                           // ... and keeps its energy when widened
    float mag = .5 + 4.5 * pow(h13(id + 3.), 4.);
    float tw = .82 + .18 * sin(T * 2.0943951 * (1. + floor(h13(id + 5.) * 3.)) + hh * 40.);   // twinkle periods 3, 1.5, 1 s
    vec3 tint = mix(vec3(1., .74, .52), vec3(.72, .84, 1.), h13(id + 17.));
    col += tint * smoothstep(rad, 0., r) * e * mag * tw * (L == 0 ? 1. : .7);
  }
  return col;
}
