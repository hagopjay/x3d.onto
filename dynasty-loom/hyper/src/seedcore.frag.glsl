#version 300 es
// seedcore.frag: the founders' seed itself, a small sun (critique fix 1). The PhysicalMaterial bead drew a flat clipped white disc (X_ITE does
// not tone-map materials); this profile is limb-darkened, from a hot centre to an orange limb, and goes through the same encode() (ACES, gamma,
// dither) as every other shader, so it never clips. It breathes with the 600 s clock (a 4 s breath, in phase with seed.frag).
// The PhysicalMaterial stays in the Appearance as the fallback when shaders are unavailable.
precision highp float; precision highp int;
uniform float uCycle, uExposure;
in vec3 vN; in vec3 vP;
out vec4 x3d_FragColor;
//#include common
void main() {
  float T = uCycle * 600.;
  float mu = clamp(abs(dot(normalize(vN), normalize(-vP))), 0., 1.);        // 1 at the centre of the disc, 0 at the limb
  float br = .8 + .2 * sin(T * 1.5707963);
  vec3 centre = vec3(1., .92, .8) * 3., limb = vec3(1., .55, .25) * .6;
  vec3 col = mix(limb, centre, pow(mu, .7)) * (.85 + .15 * br);
  x3d_FragColor = vec4(encode(col, uExposure) + dither(gl_FragCoord.xy, T), 1.);
}
