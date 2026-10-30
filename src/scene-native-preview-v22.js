import * as T from 'three';
import { addNativeEnvironment } from './environment-native-v22.js';
import { approvedCastle } from './castle-approved-v22r.js';

const query = new URLSearchParams(location.search);
const approved = query.get('preset') === 'castle-approved';
const source = approved ? approvedCastle.source : query.get('source') || 'scene';
const environment = approved ? approvedCastle.environment : query.get('environment') || 'CastleExterior';
const view = query.get('view') || 'overview';
const width = 1440, height = approved ? approvedCastle.height : 1600;
const scene = new T.Scene(); scene.background = new T.Color(0x222c28);
const renderer = new T.WebGLRenderer({ canvas: document.querySelector('#view'), antialias: true, preserveDrawingBuffer: true });
renderer.setSize(width, height); renderer.setPixelRatio(1);
renderer.outputColorSpace = T.SRGBColorSpace; renderer.toneMapping = T.NoToneMapping;
const camera = new T.PerspectiveCamera(42, width / height, .1, 1000);
if (view === 'combat') { camera.position.set(0, 87, -40); camera.lookAt(0, 0, 14); }
else if (view === 'castle') { camera.position.set(-165, 110, -55); camera.lookAt(-165, 0, 14); }
else { camera.position.set(0, 270, -145); camera.lookAt(0, 0, 0); }
try {
  const native = await addNativeEnvironment(scene, { source, environment, debugMissing: query.get('debugMissing') === '1', showGrid: approved ? approvedCastle.showGrid : query.get('grid') !== '0' });
  if (approved) {
    native.root.scale.set(1, 1, -1); native.root.updateMatrixWorld(true);
    camera.position.fromArray(approvedCastle.camera.position); camera.lookAt(...approvedCastle.camera.target);
    camera.fov = approvedCastle.camera.fov; camera.zoom = approvedCastle.camera.zoom;
    camera.updateProjectionMatrix(); camera.updateMatrixWorld(true);
  }
  renderer.render(scene, camera);
  window.nativePreview = { scene, camera, renderer, ...native, width, height, source, view, approved };
  window.ready = true;
  document.querySelector('#status').textContent = `${source} / ${view}: ${native.manifest.objects.length} native objects`;
} catch (e) { document.querySelector('#status').textContent = e.stack; window.previewError = String(e); throw e; }
