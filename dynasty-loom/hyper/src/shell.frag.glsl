#version 300 es
// shell.frag (hypersphere build; from the lookdev, shells now every 50 years from uShell0 to uTop): the glass hypersphere around the family, drawn on a proxy sphere a little larger than the analytic one (uRp > uR).
// Everything here is analytic or raymarched in pocket units; radius is time: r(year) = uR0 + (year - uY0) * uK.
// gl_FragDepth is written from the analytic entry point, so host geometry that passes between the glass and the proxy composites
// at the true surface, and the layer stays in front of the threads inside.
precision highp float; precision highp int;
uniform mat4 x3d_ProjectionMatrix, x3d_ModelViewMatrix;
uniform float uCycle, uSeed, uExposure, uFell, uY0, uK, uR0, uR, uRp, uHaze, uGain, uShell0, uTop, uInside;
uniform int uQ, uBlend;
in vec3 vRo; in vec3 vRd;
out vec4 x3d_FragColor;
//#include common
//#include sky
// logDepth (v2): 1 when X_ITE's LogarithmicDepthBuffer is on (the page sets the field); the depth is then X_ITE's own logarithmic one,
// log2(1 + w) * x3d_LogarithmicFarFactor1_2 (the formula of x3d.onto gobbler-demiurge/tools/world_layer.py), so other geometry still composites.
uniform float logDepth, x3d_LogarithmicFarFactor1_2;
float depthOf(vec3 p) { vec4 c = x3d_ProjectionMatrix * (x3d_ModelViewMatrix * vec4(p, 1.)); return logDepth > .5 ? log2(1. + c.w) * x3d_LogarithmicFarFactor1_2 : clamp(c.z / c.w * .5 + .5, 0., 1.); }
float fragDepth() { return logDepth > .5 ? log2(1. + 1. / gl_FragCoord.w) * x3d_LogarithmicFarFactor1_2 : gl_FragCoord.z; }   // the proxy's own depth
float erf1(float x) { float a = abs(x), t = 1. / (1. + .47047 * a); return sign(x) * (1. - t * (.3480242 + t * (-.0958798 + t * .7478556)) * exp(-a * a)); }
// integral of exp(-r^2/s2) along the ray between ta and tb (measured from the closest approach; d2 = squared closest distance)
float gaussInt(float d2, float s2, float ta, float tb) { float s = sqrt(s2); return .8862269 * s * exp(-d2 / s2) * (erf1(tb / s) - erf1(ta / s)); }
// integral of 1/(r^2 + e2) along the ray: a point light seen through a medium, exact
float pointInt(float d2, float e2, float ta, float tb) { float k = sqrt(d2 + e2); return (atan(tb / k) - atan(ta / k)) / k; }
vec3 timeTint(float r) { return mix(S_PAST_L, S_PRESENT_L, smoothstep(.05, 1.05, r)); }   // warm past, cool present
// STYLE (ink): 30 degree meridians and parallels on the unit sphere point n, about a pixel wide; px = a pixel's surface footprint in radians
float grat(vec3 n, float px) {
  float lat = asin(clamp(n.y, -1., 1.)), cl = cos(lat);
  float lon = atan(n.x, n.z) * 1.9098593, la = lat * 1.9098593;
  float dLon = abs(fract(lon + .5) - .5) * .5235988 * cl, dLat = abs(fract(la + .5) - .5) * .5235988;
  return max((1. - smoothstep(.25, .9, dLon / px)) * smoothstep(.12, .3, cl), 1. - smoothstep(.25, .9, dLat / px));
}
void main() {
  vec3 ro = vRo, rd = normalize(vRd);
  float pxr = max(length(fwidth(rd)), 1e-6);   // STYLE: radians per pixel, taken in uniform control flow
  float T = uCycle * 600.;
  float b = dot(ro, rd), rr = dot(ro, ro);
  float d2 = max(rr - b * b, 0.), d = sqrt(d2), tc = -b;
  bool camInProxy = rr < uRp * uRp;
  if (!gl_FrontFacing && !camInProxy) discard;            // with solid=false seen from outside, keep one layer: no double glow
  vec3 E = vec3(0.);
  float depth = fragDepth();
  float rFell = uR0 + (uFell - uY0) * uK;
  float rWave = fract(T / 12.) * 1.25 - .1;               // the energy front: leaves the seed every 12 s and runs out past the glass
  float h = uR * uR - d2;
  float in01 = 1. - smoothstep(uR * .9, uR, sqrt(rr));    // 1 with the camera inside the glass (build 2: the plunge's landing must keep its black)
  float face = mix(1., .15, in01);                         // inside, the shells' face-on whisper is cut; their limbs stay crisp
  if (S_INK > .5) {   // STYLE (ink): the glass drawn over a light ground; layers composited back to front, written with straight alpha
    vec4 acc = vec4(0.);
    float dep = fragDepth(), cr = sqrt(rr), beta = acos(clamp(dot(rd, -ro / max(cr, 1e-5)), -1., 1.));
    if (h <= 0.) {
      if (tc <= 0.) discard;
      float x = clamp((d - uR) / (uRp - uR), 0., 1.);
      over(acc, S_FROST, S_HALO_A * exp(-x * 14.) * (1. - x));
      dep = depthOf(ro + rd * tc);
    } else {
      float sq = sqrt(h), t0 = max(tc - sq, 0.), t1 = tc + sq;
      if (t1 <= 0.) discard;
      vec3 pf = (ro + rd * t1) / uR;
      if (S_GRAT_BACK > 0.) over(acc, S_ENGRAVE, S_GRAT_BACK * grat(pf, pxr * t1 / uR / max(abs(dot(pf, rd)), .2)));
      over(acc, S_FROST, S_BODY_A * clamp((t1 - t0) / (2. * uR), 0., 1.));
      for (int k = 0; k < 16; k++) {                        // the 50-year shells as limb circles, about 1.5 px, seen from outside each shell
        float yk = uShell0 + 50. * float(k);
        if (yk > uTop + .5) break;
        float rk = uR0 + (yk - uY0) * uK;
        if (rr <= rk * rk) continue;
        float woven = smoothstep(uFell + 3., uFell - 3., yk), ak = asin(clamp(rk / cr, 0., 1.));
        over(acc, mix(S_PAST, S_PRESENT, smoothstep(.05, 1.05, rk)), S_SHELL_A * exp(-pow((ak - beta) / pxr / .8, 2.)) * mix(.35, 1., woven));
      }
      if (rr > uR * uR) {
        vec3 p0 = ro + rd * t0, n = p0 / uR;
        float ci = clamp(-dot(n, rd), 0., 1.), F = .04 + .96 * pow(1. - ci, 5.);
        over(acc, S_FROST, S_FROST_A * pow(1. - ci, 2.2));                                   // frost: milky at grazing angles, clear face-on
        over(acc, S_RIMDARK, S_RIMDARK_A * exp(-pow((ci - .16) / .07, 2.)));                  // refraction cue: a dark band inside the limb
        vec3 rf = reflect(rd, n);
        over(acc, skyCol(rf, 0, T, 0., uSeed), S_REFL * F);                                   // the sweep, reflected
        float kl = max(dot(rf, normalize(vec3(.45, .62, .64))), 0.);
        over(acc, vec3(1.), S_GLINT * (smoothstep(.975, .992, kl) * .9 + .3 * pow(kl, 30.)));  // one soft softbox glint
        float limbPx = (asin(clamp(uR / cr, 0., 1.)) - beta) / pxr;
        over(acc, S_ENGRAVE, S_OUTLINE_A * (1. - smoothstep(.2, 1.6, limbPx)));               // the outline, about 1.5 px
        if (S_GRATICULE > 0.) over(acc, S_ENGRAVE, S_GRATICULE * grat(n, pxr * t0 / uR / max(ci, .2)));
        dep = depthOf(p0);
      }
    }
    gl_FragDepth = dep;
    if (acc.a < .003) discard;
    x3d_FragColor = vec4(acc.rgb / acc.a + dither(gl_FragCoord.xy, T), acc.a);
    return;
  }
  if (h <= 0.) {                                           // the ray misses the glass: atmospheric halo only
    if (tc <= 0.) discard;
    float x = clamp((d - uR) / (uRp - uR), 0., 1.);
    E = S_RIM * S_RIM_GAIN * .22 * exp(-x * 9.) * (1. - x);
    depth = depthOf(ro + rd * tc);
  } else {
    float sq = sqrt(h), t0 = max(tc - sq, 0.), t1 = tc + sq;
    if (t1 <= 0.) discard;
    if (rr > uR * uR) {                                    // camera outside the glass: fresnel limb, sky reflection, key-light glint
      vec3 p0 = ro + rd * t0, n = p0 / uR;
      float ci = clamp(-dot(n, rd), 0., 1.);
      float F = .04 + .96 * pow(1. - ci, 5.);              // Schlick, glass F0 = 0.04
      E += S_RIM * S_RIM_GAIN * (pow(1. - ci, 6.) * 1.1 + pow(1. - ci, 2.) * .05);   // a thin bright rim over a faint body
      vec3 rf = reflect(rd, n);
      if (uQ > 0) E += pow(skyCol(rf, 0, T, 0., uSeed), vec3(2.2)) * F * 2.5 * S_REFL;
      float kl = max(dot(rf, normalize(vec3(.45, .62, .64))), 0.);          // the Key light's reflection: a crisp glint over a soft sheen
      E += vec3(1., .95, .9) * (pow(kl, 600.) * 14. + pow(kl, 24.) * .35) * F * S_GLINT;
      depth = depthOf(p0);
    }                                                      // inside: keep the proxy's far wall, so the threads stay crisp in front
    for (int k = 0; k < 16; k++) {                         // time shells every 50 years (uShell0, uShell0 + 50, ... up to uTop): thin emitting spheres
      float yk = uShell0 + 50. * float(k);
      if (yk > uTop + .5) break;
      float rk = uR0 + (yk - uY0) * uK, hk = rk * rk - d2;
      if (hk <= 0.) continue;
      float sk = sqrt(hk), ck = sk / rk;                   // |cos| between the ray and the shell normal
      float woven = smoothstep(uFell + 3., uFell - 3., yk);
      float pulse = 1. + S_SHELL_FRONT * exp(-pow((rk - rWave) / .045, 2.));
      float line = .0012 * face / max(ck, .05) + .045 * exp(-ck * ck / .012);   // a whisper face-on (path ~ 1/cos), a crisp line at the limb
      vec3 c = timeTint(rk) * line * pulse * mix(.12, 1., woven);
      if (tc - sk > t0) E += c;                            // near crossing
      if (tc + sk > t0) E += c * .5;                       // far crossing, dimmer
    }
    float hf = rFell * rFell - d2;                         // the fell: the shell being woven now glows hot
    if (hf > 0. && rFell < uR) {
      float sf = sqrt(hf), cf = sf / rFell;
      vec3 c = vec3(1., .80, .52) * (.002 * face / max(cf, .05) + .08 * exp(-cf * cf / .012));
      if (tc - sf > t0) E += c;
      if (tc + sf > t0) E += c * .45;
    }
    float ta = t0 - tc, tb = t1 - tc;
    // build 2 (critique fix 1): with the camera inside the glass every ray crosses the whole haze, and the body fogged the plunge's landing.
    // uInside scales the haze when the camera is inside, decided here from the camera's own radius, so it holds in any host with no page.
    float kin = mix(uInside, 1., smoothstep(uR * .9, uR, sqrt(rr)));
    E += S_HAZE * gaussInt(d2, .36, ta, tb) * .02 * uHaze * kin * S_HAZE_GAIN;     // haze body: analytic, every tier
    if (uQ > 0) {                                          // haze flow: radial streaks and outward ripples, glow accumulated along the ray
      int N = uQ == 1 ? 12 : 28;
      float dt = (t1 - t0) / float(N), j = h13(vec3(gl_FragCoord.xy, floor(T * 30.)));
      vec3 acc = vec3(0.);
      for (int i = 0; i < 28; i++) {
        if (i >= N) break;
        float t = t0 + (float(i) + j) * dt;
        vec3 p = ro + rd * t; float r = length(p);
        float st = fbm(p / max(r, 1e-4) * 3.3 + uSeed * 3.1, uQ == 1 ? 3 : 5);   // noise of direction only: streaks that point outward
        float rip = .6 + .4 * sin(6.2831853 * (r / .15 - T / 4.));              // ripples: 0.15 units every 4 s, outward
        float fr = exp(-pow((r - rWave) / .06, 2.));
        float woven = smoothstep(rFell + .04, rFell - .04, r);
        float dens = exp(-r * r / .5) * smoothstep(.5, .9, st) * rip * (.25 + .75 * woven) + fr * .5 * smoothstep(.55, .9, st);
        acc += dens * mix(S_HAZE * 1.25, timeTint(r), .55);
      }
      E += acc * dt * .08 * uHaze * kin * S_FLOW;
    }
    // the founders' seed has its own glow layer (seed.frag), so it blooms over the seed from inside the glass as well
  }
  gl_FragDepth = depth;
  x3d_FragColor = glowOut(encode(knee(E, .005 * in01) * uGain, uExposure) + dither(gl_FragCoord.xy, T), uBlend);
}
