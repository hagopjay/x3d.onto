#version 300 es
// ray.vert: the proxy-geometry vertex shader (the pocket pages' pattern). The ray is set up in the shape's own local space with
// inverse(x3d_ModelViewMatrix), so the fragment shader works in pocket units whatever Transform scale nests it in a host.
precision highp float;
uniform mat4 x3d_ProjectionMatrix, x3d_ModelViewMatrix;
in vec4 x3d_Vertex;
out vec3 vRo; out vec3 vRd;
void main() {
  vec4 vp = x3d_ModelViewMatrix * x3d_Vertex;
  mat4 inv = inverse(x3d_ModelViewMatrix);          // eye space -> local space
  vRo = (inv * vec4(0., 0., 0., 1.)).xyz;           // the camera in local units
  vRd = (inv * vec4(vp.xyz, 1.)).xyz - vRo;
  gl_Position = x3d_ProjectionMatrix * vp;
}
