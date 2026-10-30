#version 300 es
// ring.vert: the host's pewter armillary (and the seed disc). Eye-space position and normal for ring.frag (the tube scale is uniform, so mat3(modelview) keeps normals).
precision highp float;
uniform mat4 x3d_ProjectionMatrix, x3d_ModelViewMatrix;
in vec4 x3d_Vertex;
in vec3 x3d_Normal;
out vec3 vN; out vec3 vP;
void main() {
  vec4 pe = x3d_ModelViewMatrix * x3d_Vertex;
  vP = pe.xyz; vN = mat3(x3d_ModelViewMatrix) * x3d_Normal;
  gl_Position = x3d_ProjectionMatrix * pe;
}
