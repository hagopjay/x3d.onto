#version 300 es
// sky.frag: the host sky on an inverted proxy sphere. Opaque; direction only, so it reads as infinitely far.
precision highp float; precision highp int;
uniform float uCycle, uSeed, uExposure;
uniform int uQ;
in vec3 vRo; in vec3 vRd;
out vec4 x3d_FragColor;
//#include common
//#include sky
void main() {
  vec3 d = normalize(vRd);
  float T = uCycle * 600.;
  float pxa = length(fwidth(d));
  vec3 c = skyCol(d, uQ, T, pxa, uSeed);
  x3d_FragColor = vec4(c + grainAt(gl_FragCoord.xy, T) + dither(gl_FragCoord.xy, T), 1.);   // STYLE: the backdrop is display sRGB
}
