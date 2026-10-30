#version 300 es
// fiber.vert (hypersphere build): camera-facing ribbons, from the lookdev. Each polyline point is two vertices (aInfo.x = side -1 / +1)
// sharing position and tangent; the shader pushes them apart across the view. Width is in pocket units (uWidth) with a pixel floor
// (uMinPx) and ceiling (uMaxPx); when the floor wins, vFade lowers the intensity so a far thread keeps its energy.
// Selection (build 2, critique fix 2): uPick is the subject (a person index, -1 none) and uLine the lineage the page writes for the stop or
// the pick (the subject, a spouse, the line back to the founders; -1 ends the list). vSel: -1 nothing selected, 2 the subject's own threads
// (its life, its spawn arc, its marriages), 1 the lineage (a life in the list, a marriage between two people in it), 0 everything else.
precision highp float; precision highp int;
uniform mat4 x3d_ProjectionMatrix, x3d_ModelViewMatrix;
uniform ivec4 x3d_Viewport;
uniform float uWidth, uMinPx, uMaxPx, uPick;
uniform float uLine[32];
uniform int uPass;   // 1 = the glow pass: pushed 0.2 percent deeper along each eye ray (same pixels), so it never z-fights its own opaque core
in vec4 x3d_Vertex;
in vec4 x3d_Color;
in vec3 aTan;      // unit tangent along the thread
in vec4 aInfo;     // side (-1/+1), year, seed (0..1), kind (0 life, 1 spawn / move / root arc, 2 marriage arc, 3 close marriage arc)
in vec4 aAux;      // along (kind 0: 0..1 from birth to death; kind 1-3: pocket units from the arc's start, for dashes), estimated (1 = dashed), person A, person B
out vec3 vDye; out float vS, vYear, vSeed, vKind, vEst, vFade, vPa, vPb, vSel, vAlong;
float inLine(float x) {
  for (int i = 0; i < 32; i++) { float v = uLine[i]; if (v < -.5) break; if (abs(v - x) < .5) return 1.; }
  return 0.;
}
void main() {
  vec4 pe = x3d_ModelViewMatrix * x3d_Vertex;
  vec3 te = mat3(x3d_ModelViewMatrix) * aTan;
  vec3 sd = cross(te, normalize(-pe.xyz));
  float sl = length(sd);
  sd = sl > 1e-6 ? sd / sl : vec3(1., 0., 0.);
  float sc = length(x3d_ModelViewMatrix[0].xyz);                       // the nesting scale (uniform)
  float kind = aInfo.w;
  float wk = kind > 2.5 ? .9 : (kind > 1.5 ? .75 : (kind > .5 ? .7 : 1.));
  float taper = kind < .5 ? mix(.3, 1., smoothstep(0., .08, aAux.x)) : 1.;   // a life swells out of its spawn point
  float wEye = uWidth * wk * taper * sc;
  float px = 2. * max(-pe.z, 1e-4) / (x3d_ProjectionMatrix[1][1] * float(x3d_Viewport.w));   // eye units per pixel at this depth
  float w = clamp(wEye, uMinPx * px, uMaxPx * px);
  vFade = min(wEye / w, 1.) * smoothstep(.015, .06, -pe.z / sc);
  pe.xyz += sd * aInfo.x * w;
  if (uPass == 1) pe.xyz *= 1.002;
  gl_Position = x3d_ProjectionMatrix * pe;
  float pa = aAux.z, pb = aAux.w, sel = -1.;
  if (uPick > -.5) {
    bool own = abs(pa - uPick) < .5 || abs(pb - uPick) < .5;
    sel = own ? 2. : (kind > 1.5 ? inLine(pa) * inLine(pb) : inLine(pa));
  }
  vDye = x3d_Color.rgb; vS = aInfo.x; vYear = aInfo.y; vSeed = aInfo.z; vKind = kind; vEst = aAux.y; vPa = pa; vPb = pb; vSel = sel; vAlong = aAux.x;
}
