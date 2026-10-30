import * as T from 'three';

// Layer the existing native sampled leg poses under the existing native attack
// snapshots. This is continuous vertex-pose blending, not claimed bone layers.
// Head, arms and bow retain their release pose and hand origin exactly.
export function addArcherLocomotionLayer(batches, material, clips) {
  const phases = clips.move.phases;
  const first = batches.get('archer/move/0').mesh.geometry;
  if (first.index) throw Error('Locomotion atlas expects native nonindexed snapshots');
  const vertices = first.attributes.position.count;
  const width = T.MathUtils.ceilPowerOfTwo(vertices);
  const pixels = new Float32Array(width * phases * 4);
  for (let f = 0; f < phases; f++) {
    const position = batches.get(`archer/move/${f}`).mesh.geometry.attributes.position;
    if (position.count !== vertices) throw Error('Walk pose topology changed');
    for (let v = 0; v < vertices; v++) {
      const i = (f * width + v) * 4;
      pixels[i] = position.getX(v); pixels[i + 1] = position.getY(v); pixels[i + 2] = position.getZ(v); pixels[i + 3] = 1;
    }
  }
  const texture = new T.DataTexture(pixels, width, phases, T.RGBAFormat, T.FloatType);
  texture.minFilter = texture.magFilter = T.NearestFilter; texture.generateMipmaps = false; texture.needsUpdate = true;
  for (const [key, batch] of batches) if (key.startsWith('archer/')) {
    if (batch.mesh.geometry.attributes.position.count !== vertices) throw Error('Attack/walk native topology mismatch');
    batch.locomotion = new T.InstancedBufferAttribute(new Float32Array(1024 * 2), 2);
    batch.mesh.geometry.setAttribute('walkingCycle', batch.locomotion);
  }
  const prior = material.onBeforeCompile;
  material.onBeforeCompile = shader => {
    prior(shader);
    shader.uniforms.walkPoseTexture = { value: texture };
    shader.uniforms.walkPoseSize = { value: new T.Vector2(width, phases) };
    shader.vertexShader = 'uniform sampler2D walkPoseTexture; uniform vec2 walkPoseSize; attribute vec2 walkingCycle;\n' + shader.vertexShader;
    shader.vertexShader = shader.vertexShader.replace('vHit=hit;', `
      float gait = fract(walkingCycle.x) * walkPoseSize.y;
      float p0 = floor(gait), p1 = mod(p0 + 1.0, walkPoseSize.y);
      float u = (float(gl_VertexID) + .5) / walkPoseSize.x;
      vec3 w0 = texture2D(walkPoseTexture, vec2(u, (p0 + .5) / walkPoseSize.y)).xyz;
      vec3 w1 = texture2D(walkPoseTexture, vec2(u, (p1 + .5) / walkPoseSize.y)).xyz;
      float legs = 1.0 - smoothstep(.42, .78, restPosition.y);
      transformed = mix(transformed, mix(w0, w1, fract(gait)), legs * walkingCycle.y);
      vHit=hit;`);
  };
  material.customProgramCacheKey = () => 'v22r-native-archer-walk-under-attack';
  return { method: 'Native nonindexed vertex-pose atlas, continuous gait interpolation, height mask .42–.78; upper-body release unchanged', phases, vertices, textureSize: [width, phases], source: clips.move.nativeClip };
}
