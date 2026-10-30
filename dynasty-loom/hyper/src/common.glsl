// common.glsl: hashes, value noise, fbm, tone map and the glow output, shared by every fragment shader (the generator pastes it in).
float h13(vec3 p) { p = fract(p * .1031); p += dot(p, p.zyx + 31.32); return fract((p.x + p.y) * p.z); }
float vnoise(vec3 x) {
  vec3 i = floor(x), f = fract(x); f = f * f * (3. - 2. * f);
  return mix(mix(mix(h13(i), h13(i + vec3(1., 0., 0.)), f.x), mix(h13(i + vec3(0., 1., 0.)), h13(i + vec3(1., 1., 0.)), f.x), f.y),
             mix(mix(h13(i + vec3(0., 0., 1.)), h13(i + vec3(1., 0., 1.)), f.x), mix(h13(i + vec3(0., 1., 1.)), h13(i + vec3(1., 1., 1.)), f.x), f.y), f.z);
}
// fbm normalised to 0..1 whatever the octave count, so a lower tier keeps the same brightness and only loses fine detail
float fbm(vec3 p, int oct) {
  float a = .5, s = 0., n = 0.;
  for (int i = 0; i < 7; i++) { if (i >= oct) break; s += a * vnoise(p); n += a; p = p * 2.03 + vec3(1.7, 9.2, 3.1); a *= .5; }
  return s / max(n, 1e-4);
}
float aces1(float x) { return clamp((x * (2.51 * x + .03)) / (x * (2.43 * x + .59) + .14), 0., 1.); }
vec3 aces(vec3 c) { return clamp((c * (2.51 * c + .03)) / (c * (2.43 * c + .59) + .14), 0., 1.); }   // Narkowicz ACES fit
vec3 encode(vec3 lin, float exposure) { return pow(aces(lin * exposure), vec3(.4545)); }             // tone map, then display gamma
// a soft black knee in linear light (build 2): the ACES toe plus gamma lifts tiny energies a lot (E 0.001 shows as 0.02), so a faint far field
// reads as fog; E * E / (E + k) leaves E >> k alone and pushes E << k toward black. k = 0 is the identity.
vec3 knee(vec3 E, float k) { return E * E / (E + vec3(k + 1e-9)); }
float dither(vec2 fc, float t) { return (h13(vec3(fc, floor(t * 60.))) - .5) / 255.; }                // one 8-bit step of noise: no banding
// The glow output. Standard X3D blends SRC_ALPHA, ONE_MINUS_SRC_ALPHA; writing (e / max(e), max(e)) turns that into
// out = e + dst * (1 - max(e)), a screen blend: light adds, nothing darkens, and the order of the layers barely matters.
// With X_ITE's BlendMode (ONE, ONE) the page sets uBlend = 1 and the layer is purely additive.
vec4 glowOut(vec3 e, int blend) {
  float a = max(max(e.r, e.g), e.b);
  if (a < .002) discard;
  if (blend == 1) return vec4(e, 1.);
  return vec4(e / a, a);
}
