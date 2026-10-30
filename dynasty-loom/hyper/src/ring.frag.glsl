#version 300 es
// ring.frag: polished pewter (build 3: was gold; the dye owns gold), lit in eye space (a key from upper right, a cool Blinn highlight, a
// Fresnel rim), tone-mapped like every other
// shader here. It replaces the PhysicalMaterial look, which X_ITE drew white without its tone mapping and near black with it (build-1 frames);
// the PhysicalMaterial stays in the Appearance as the fallback when shaders are unavailable.
precision highp float; precision highp int;
uniform float uCycle, uExposure;
uniform vec3 uTint;   // the metal's colour (PEWTER in the generator)
in vec3 vN; in vec3 vP;
out vec4 x3d_FragColor;
//#include common
void main() {
  vec3 N = normalize(vN), V = normalize(-vP);
  if (dot(N, V) < 0.) N = -N;
  float c = clamp(dot(N, V), 0., 1.);
  vec3 L = normalize(vec3(.45, .62, .64)), H = normalize(L + V);
  vec3 metal = uTint;
  float diff = clamp(dot(N, L), 0., 1.), spec = pow(clamp(dot(N, H), 0., 1.), 48.), rim = pow(1. - c, 3.);
  vec3 col = metal * (.05 + .34 * diff) + vec3(.92, .95, 1.) * spec * 1.3 + metal * rim * .45;
  x3d_FragColor = vec4(encode(col, uExposure) + dither(gl_FragCoord.xy, uCycle * 600.), 1.);
}
