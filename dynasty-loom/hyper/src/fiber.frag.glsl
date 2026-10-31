#version 300 es
// fiber.frag (hypersphere build): one source, two passes. uPass 0 = the hot core (opaque, narrow, writes depth); uPass 1 = the soft glow
// (transparent, wide, screen or additive blend). Colour from the dye, pulses running outward along time, the energy front shared with the
// glass, and the time cut: years after uFell are not woven yet and fade to a ghost.
// Selection (build 2): the tone map runs on the thread's own energy; the selection acts after it, in display space: the subject keeps full
// value and a hotter glow, the lineage stays near full (core 0.8, glow 0.7), the rest keeps only a slate glow (0.22, see build 3 below).
// uFocus (0..1) blends the selection in and out, so the page can ease it at a stop's arrival.
// Dashes (build 2): an estimated life is dashed along time (4 years on, 3 off); an estimated arc lies on one shell (one year), so it is
// dashed along its length instead (vAlong, pocket units). Keyed on the year, a whole arc was on or off: the Habsburg 1672 marriage vanished.
// Build 3 (critique ranks 1 and 2): with a selection on, the rest has NO core: it discards in pass 0, so it writes no depth and can never
// draw a dark opaque notch across the subject or the sky; it lives only in the glow pass, which can only add light, tinted a cool slate
// (a faint blue-grey constellation the subject floats in). While uFocus eases in, the glow pass carries a narrow core-shaped term that fades
// with (1 - uFocus), so the rest's cores dim out instead of popping. Colour keeps its chroma: the dye is pushed 1.4x away from its luminance
// before it is normalised to full value (the low-chroma ramp steps had turned cream-white), and a dyed core mixes less toward white.
precision highp float; precision highp int;
uniform float uCycle, uFell, uY0, uR0, uK, uExposure, uGhost, uGain, uFocus;
uniform int uQ, uPass, uBlend;
in vec3 vDye; in float vS, vYear, vSeed, vKind, vEst, vFade, vPa, vPb, vSel, vAlong, vSheen;
out vec4 x3d_FragColor;
//#include common
void main() {
  float T = uCycle * 600.;
  vec3 neon = clamp(mix(vec3(dot(vDye, vec3(.2126, .7152, .0722))), vDye, S_CHROMA), 0., 1.);   // chroma kept: 1.4x away from the luminance,
  neon /= mix(1., max(max(neon.r, neon.g), max(neon.b, 1e-3)), S_VALUE_NORM);                                     // then the dye at full value: same hue, neon bright
  float mx = max(max(vDye.r, vDye.g), vDye.b), dyed = step(.3, (mx - min(min(vDye.r, vDye.g), vDye.b)) / max(mx, 1e-3));   // ecru (share 0) is ~0.15
  float woven = smoothstep(uFell + 1.5, uFell - 1.5, vYear);
  float tip = vKind < .5 ? exp(-max(uFell - vYear, 0.) / 2.5) * woven : 0.;  // the newest woven years of a life burn white
  float dash = vEst > .5 ? step(fract(vKind < .5 ? vYear / 7. : vAlong / .028), .57) : 1.;
  float ph = vYear / 75. - T / 3. + (uQ > 1 ? vSeed * .35 : 0.);            // pulses: 75 years apart, 25 years per second outward
  float pulse = pow(.5 + .5 * cos(6.2831853 * ph), 24.);
  float rWave = fract(T / 12.) * 1.25 - .1;                                 // the 12 s energy front, in radius, shared with the glass
  float yWave = uY0 + (rWave - uR0) / uK;
  float front = exp(-pow((vYear - yWave) * uK / .03, 2.));
  float kg = vKind > 2.5 ? 1.55 : (vKind > 1.5 ? 1.2 : (vKind > .5 ? .75 : 1.));   // a close marriage (phi > 0) is brighter, and drawn doubled
  float I = (1. + S_PULSE * pulse + S_FRONT * front + S_TIP * tip) * kg * uGain;
  float lum = pow(aces1(I * uExposure * .9), .4545);
  float est = vEst > .5 ? .55 : 1.;                                         // an estimated stretch is also translucent
  // the selection, after the tone map: -1 none, 2 subject, 1 lineage, 0 the rest
  bool rest = vSel > -.5 && vSel < .5;
  float kc = vSel > .5 && vSel < 1.5 ? .8 : 1.;
  float kgl = vSel < -.5 ? 1. : (vSel > 1.5 ? 1.15 : (vSel > .5 ? .7 : S_REST_GLOW));
  float hot = vSel > 1.5 ? .12 : 0.;
  kc = mix(1., kc, uFocus); kgl = mix(1., kgl, uFocus); hot *= uFocus;
  float white = clamp(mix(S_WHITE_ECRU, S_WHITE, dyed) + .2 * S_TIP * tip + .19 * S_PULSE * pulse + hot, 0., 1.);
  float c = 1. - vS * vS;
  vec3 core = mix(neon, vec3(1.), white * c) * lum * mix(1., est, .5);       // the core's colour before the pixel-floor fade
  if (rest) neon = mix(neon, S_REST_L, .7 * uFocus);             // the rest: a cool slate, not a grey (build 3)
  if (S_INK > .5) {   // STYLE (ink): pigment on a light ground; straight alpha, no tone map, no pulses, no front, no white tips
    float q2 = vS * vS, l0 = dot(vDye, vec3(.2126, .7152, .0722));
    vec3 ink = clamp(mix(vec3(l0), vDye, S_CHROMA), 0., 1.) * S_INK_VALUE;
    vec3 silk = ink * (1. - S_ROUND * q2) + S_SHEEN * pow(vSheen, 24.) * (1. - q2);   // a rounded thread; silk catches the key along its length
    if (uPass == 0) {
      if (woven < .5 || dash < .5) discard;
      if (rest && uFocus > .01) discard;                                        // no core for the rest under a selection (as v3)
      vec3 c = vSel > .5 && vSel < 1.5 ? mix(silk, S_GROUND_TOP, .22 * uFocus) : silk;   // the lineage a shade lighter than the subject
      x3d_FragColor = vec4(mix(c, S_GROUND_TOP, (1. - est) * .55), 1.);         // an estimated stretch is paler as well as dashed
    } else {
      float vis = mix(uGhost, 1., woven) * mix(.45, 1., dash) * est;
      float a = S_BLEED_A * exp(-q2 * S_BLEED_K) * vis * vFade;
      vec3 c = ink;
      if (rest && uFocus > .01) {
        c = mix(ink, S_REST, uFocus);
        a = mix(a, S_REST_A * exp(-q2 * 3.) * vis * vFade, uFocus);
        if (woven > .5 && dash > .5) a = max(a, exp(-q2 * 60.) * (1. - uFocus));   // the core, fading out
      }
      if (a < .004) discard;
      x3d_FragColor = vec4(c, a);
    }
    return;
  }
  if (uPass == 0) {
    if (woven < .5 || dash < .5) discard;
    if (rest && uFocus > .01) discard;                                       // no core, no depth: the rest cannot occlude (build 3)
    x3d_FragColor = vec4(core * (.7 + .3 * vFade) * kc, 1.);
  } else {
    float s2 = vS * vS;
    float g = .7 * exp(-s2 * 3.2) + .3 * exp(-s2 * 14.);
    float vis = mix(uGhost, 1., woven) * mix(.45, 1., dash) * est;
    vec3 e = neon * g * lum * vis * vFade * S_GLOW * kgl;
    if (rest && uFocus > .01 && woven > .5 && dash > .5) e += core * (.7 + .3 * vFade) * exp(-s2 * 60.) * (1. - uFocus);   // the core, fading out
    x3d_FragColor = glowOut(e + dither(gl_FragCoord.xy, T), uBlend);
  }
}
