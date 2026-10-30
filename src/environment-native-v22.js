import * as T from 'three';

// Geometry/placement comes ONLY from Unity's evaluated native scene export.
// No FBX import, hierarchy reinterpretation, model scale, or handmade ground.
export async function addNativeEnvironment(scene, { source = 'scene', environment = 'CastleExterior', debugMissing = false, showGrid = true } = {}) {
  if (!['scene', 'prefab'].includes(source)) throw Error('source must be scene or prefab');
  if (!['CastleExterior', 'ArenaScene', 'NewScene'].includes(environment)) throw Error('Unknown native environment');
  const base = environment === 'NewScene' ? '/native-scenes/NewScene/' : `/native-scenes/${environment}-${source}/`;
  const manifest = await fetch(`${base}manifest.json`).then(r => { if (!r.ok) throw Error(r.status); return r.json(); });
  const audit = { source: manifest.source, unityVersion: manifest.unityVersion, nativeObjects: manifest.objects.length, objects: [], warnings: [...manifest.warnings], textureBindings: [] };
  const loader = new T.TextureLoader();
  const materials = await Promise.all(manifest.materials.map(async m => {
    if (/Gird|Grid/i.test(m.name)) {
      const binding = m.textures.find(t => t.property === '_Mask');
      if (binding) {
        // Package filename says PNG but bytes are DDS; losslessly decoded for HTML image support.
        const mask = await loader.loadAsync('/native-scenes/textures/08ce35de-decoded.png');
        mask.wrapS = mask.wrapT = T.RepeatWrapping;
        const scalar = (name, fallback) => m.floats?.find(x => x.property === name)?.value ?? fallback;
        const color = (name, fallback) => { const c = m.colors?.find(x => x.property === name)?.value; return c ? new T.Vector4(c.r, c.g, c.b, c.a) : fallback; };
        const c1 = color('_GirdColor01', new T.Vector4(1, .9739443, .90880495, .7411765));
        const c2 = color('_GirdColor02', new T.Vector4(1, 1, 1, 1));
        const off = color('_Offset', new T.Vector4(.25, 0, 0, 0));
        const mat = new T.ShaderMaterial({
          uniforms: { mask: { value: mask }, gridScale: { value: scalar('_Scale', 6) }, gridOffset: { value: new T.Vector2(off.x, off.y) }, maskST: { value: new T.Vector4(binding.scale.x, binding.scale.y, binding.offset.x, binding.offset.y) }, color1: { value: c1 }, color2: { value: c2 } },
          vertexShader: 'varying vec2 vUv; varying vec3 vWorld; void main(){vUv=uv;vec4 world=modelMatrix*vec4(position,1.);vWorld=world.xyz;gl_Position=projectionMatrix*viewMatrix*world;}',
          fragmentShader: `uniform sampler2D mask;uniform float gridScale;uniform vec2 gridOffset;uniform vec4 maskST,color1,color2;varying vec2 vUv;varying vec3 vWorld;
            void main(){vec2 uv=.5+(vWorld.xz/gridScale+gridOffset);vec2 dx=dFdx(uv),dy=dFdy(uv);vec2 lengths=sqrt(vec2(dot(dx,dx),dot(dy,dy)));vec2 grid=clamp(((abs(fract(uv+.25)-.5)*4.-1.)*(.35/max(lengths,vec2(.000001)))),-1.,1.);float factor=clamp(.5+.5*grid.x*grid.y*sqrt(clamp(1.1-max(lengths.x,lengths.y),0.,1.)),0.,1.);vec4 c=mix(color1,color2,factor);float amount=color1.a*color2.a*texture2D(mask,vUv*maskST.xy+maskST.zw).r;gl_FragColor=vec4(mix(vec3(1.),c.rgb,amount),1.);}`,
          blending: T.MultiplyBlending, premultipliedAlpha: true, transparent: true, depthWrite: false, side: T.DoubleSide,
        });
        mat.name = m.name; mat.userData.native = m; mat.userData.unsupported = false;
        audit.textureBindings.push({ material: m.name, property: '_Mask', texture: binding.path, missing: false, shader: 'source Grid.shader formula, DstColor Zero multiplication' });
        return mat;
      }
    }
    let map = null;
    const binding = m.textures.find(t => t.property === m.textureProperty);
    if (m.texturePath) {
      map = await loader.loadAsync(`/assets/imported/${m.texturePath}`);
      map.colorSpace = T.SRGBColorSpace; map.anisotropy = 8;
      // Mesh UVs are native Unity UVs; Three's default image flipY matches them.
      map.wrapS = map.wrapT = T.RepeatWrapping;
      if (binding) { map.repeat.set(binding.scale.x, binding.scale.y); map.offset.set(binding.offset.x, binding.offset.y); }
    }
    const transparent = m.renderQueue >= 3000;
    const mat = new T.MeshBasicMaterial({ map, color: map ? 0xffffff : 0xff00ff, side: T.DoubleSide, transparent, alphaTest: transparent ? .08 : 0, depthWrite: !transparent });
    mat.name = m.name;
    mat.userData.native = m;
    mat.userData.unsupported = !map;
    audit.textureBindings.push({ material: m.name, property: m.textureProperty, texture: m.texturePath, missing: !map });
    if (!map) audit.warnings.push(`${m.name}: source shader/texture dependencies unresolved; overlay hidden unless debugMissing=1`);
    return mat;
  }));
  const geometries = await Promise.all(manifest.meshes.map(async m => {
    const b = await fetch(base + m.file).then(r => r.arrayBuffer());
    const g = new T.BufferGeometry();
    g.setAttribute('position', new T.BufferAttribute(new Float32Array(b, m.positionOffset, m.vertexCount * 3), 3));
    if (m.normalCount === m.vertexCount) g.setAttribute('normal', new T.BufferAttribute(new Float32Array(b, m.normalOffset, m.normalCount * 3), 3));
    if (m.uvCount === m.vertexCount) g.setAttribute('uv', new T.BufferAttribute(new Float32Array(b, m.uvOffset, m.uvCount * 2), 2));
    let all = [], offset = 0;
    m.submeshes.forEach((s, i) => {
      if (s.topology !== 0) throw Error(`Unsupported topology ${s.topology}`);
      const indices = new Int32Array(b, s.offset, s.count);
      all.push(...indices); g.addGroup(offset, s.count, i); offset += s.count;
    });
    g.setIndex(all); g.computeBoundingBox(); g.computeBoundingSphere();
    g.name = m.name;
    return g;
  }));
  const root = new T.Group(); root.name = `Unity-native-${source}`;
  for (const o of manifest.objects) {
    const mats = o.materials.map(i => materials[i] || new T.MeshBasicMaterial({ color: 0xff00ff, side: T.DoubleSide }));
    const mesh = new T.Mesh(geometries[o.mesh], mats);
    mesh.name = o.path; mesh.matrixAutoUpdate = false; mesh.matrix.fromArray(o.matrix);
    mesh.visible = debugMissing || !mats.every(m => m.userData.unsupported);
    if (!showGrid && (/(^|\/)Gird$/.test(o.path) || mats.some(m => /Gird|Grid/i.test(m.name)))) mesh.visible = false;
    // A single native world matrix already includes all FBX and prefab factors.
    root.add(mesh);
    audit.objects.push({ name: o.path, visible: mesh.visible, matrix: o.matrix, nativeBounds: { center: o.boundsCenter, size: o.boundsSize } });
  }
  scene.add(root); root.updateMatrixWorld(true);
  return { root, manifest, audit };
}
