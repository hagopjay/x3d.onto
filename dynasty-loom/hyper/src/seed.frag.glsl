#version 300 es
// seed.frag: a breathing point glow integrated analytically along the ray inside a proxy sphere. One source, two uses: the founders' seed
// (SeedGlow) and the subject bead of a close shot (BeadGlow). Everything runs in units of the proxy radius uRg, so the profile is the same at
// any size and only the gains differ. Build-2 kernel (critique fix 1): the halo integrand is 1/(r^2 + e^2)^2 - w, steeper than the old
// 1/(r^2 + e^2), so the light stays near the core and the view around it keeps its black. Its integral has a closed form:
//   F(t) = t / (2 k^2 (t^2 + k^2)) + atan(t / k) / (2 k^3),  k^2 = d^2 + e^2 (d = the ray's closest approach),
// and w = 1 / (1 + e^2)^2 makes the integrand zero at the proxy, so the proxy never shows an edge. uRing > 0 adds a thin ring around the
// core at that closest-approach radius: a circle that always faces the camera (a marriage bead).
// gl_FragDepth sits uZ proxy radii along the ray from the closest approach: the bead's glow in front of its centre (uZ < 0); the seed's just
// behind its centre (uZ > 0), so the opaque seed disc (SeedCore) occludes its own bloom and never clips. A cubic window and the black knee
// (uKnee) keep the far field black (build 2: the faint tail of the old halo was the plunge's fog).
precision highp float; precision highp int;
uniform mat4 x3d_ProjectionMatrix, x3d_ModelViewMatrix;
uniform float uCycle, uExposure, uRg, uGain, uE2, uS2, uHalo, uCore, uPeriod, uRing, uKnee, uZ;
uniform vec3 uHaloTint, uCoreTint;
uniform int uBlend;
in vec3 vRo; in vec3 vRd;
out vec4 x3d_FragColor;
//#include common
float depthOf(vec3 p) { vec4 c = x3d_ProjectionMatrix * (x3d_ModelViewMatrix * vec4(p, 1.)); return clamp(c.z / c.w * .5 + .5, 0., 1.); }
float erf1(float x) { float a = abs(x), t = 1. / (1. + .47047 * a); return sign(x) * (1. - t * (.3480242 + t * (-.0958798 + t * .7478556)) * exp(-a * a)); }
float gaussInt(float d2, float s2, float ta, float tb) { float s = sqrt(s2); return .8862269 * s * exp(-d2 / s2) * (erf1(tb / s) - erf1(ta / s)); }
float invSq(float t, float k2) { float k = sqrt(k2); return t / (2. * k2 * (t * t + k2)) + atan(t / k) / (2. * k2 * k); }
void main() {
  vec3 ro = vRo / uRg, rd = normalize(vRd);                                 // proxy radius = 1
  float T = uCycle * 600.;
  float b = dot(ro, rd), rr = dot(ro, ro), d2 = max(rr - b * b, 0.), tc = -b;
  bool camIn = rr < 1.;
  if (!gl_FrontFacing && !camIn) discard;
  float h = 1. - d2;
  if (h <= 0.) discard;
  float sq = sqrt(h), t0 = max(tc - sq, 0.), t1 = tc + sq;
  if (t1 <= 0.) discard;
  float ta = t0 - tc, tb = t1 - tc;
  float br = .8 + .2 * sin(T * 6.2831853 / uPeriod);                       // the breath (4 s seed, 2 s bead); every period divides the 600 s clock
  float e2 = uE2 * br, k2 = d2 + e2, w = 1. / ((1. + e2) * (1. + e2));
  float halo = max(invSq(tb, k2) - invSq(ta, k2) - (tb - ta) * w, 0.) * h * h * h;
  vec3 E = uHaloTint * halo * uHalo * br + uCoreTint * gaussInt(d2, uS2 * br, ta, tb) * uCore * br;
  if (uRing > 0. && tc > 0.) { float dr = (sqrt(d2) - uRing) / .016; E += uCoreTint * .75 * exp(-dr * dr) * (.85 + .15 * br); }
  gl_FragDepth = depthOf((ro + rd * max(tc + uZ, t0 + 1e-3)) * uRg);
  x3d_FragColor = glowOut(encode(knee(E, uKnee) * uGain, uExposure) + dither(gl_FragCoord.xy, T), uBlend);
}
