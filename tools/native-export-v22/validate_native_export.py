"""Validate Unity-exported binary mesh/world transforms against Renderer.bounds."""
import json
from pathlib import Path
import numpy as np

root = Path('C:/Users/89trillion/PveMontageShot01V22-UnityExport/output/native-scenes')
results = {}
for folder in sorted(p for p in root.iterdir() if p.is_dir()):
    d = json.loads((folder/'manifest.json').read_text())
    assert not d['warnings'], d['warnings']
    max_error = 0.
    for obj in d['objects']:
        mesh = d['meshes'][obj['mesh']]
        binary = (folder/mesh['file']).read_bytes()
        pos = np.frombuffer(binary, '<f4', mesh['vertexCount']*3, mesh['positionOffset']).reshape(-1, 3)
        matrix = np.array(obj['matrix']).reshape(4, 4, order='F')
        world = np.column_stack([pos, np.ones(len(pos))]) @ matrix.T
        low, high = world[:, :3].min(0), world[:, :3].max(0)
        center = np.array([obj['boundsCenter'][k] for k in 'xyz'])
        size = np.array([obj['boundsSize'][k] for k in 'xyz'])
        # Unity Renderer.bounds transforms the local AABB, not only vertices.
        local_low, local_high = pos.min(0), pos.max(0)
        import itertools
        corners = np.array(list(itertools.product(*zip(local_low, local_high))))
        transformed = np.column_stack([corners, np.ones(8)]) @ matrix.T
        error = max(np.max(np.abs(transformed[:, :3].min(0)-(center-size/2))), np.max(np.abs(transformed[:, :3].max(0)-(center+size/2))))
        max_error = max(max_error, float(error))
        assert error < .002, (obj['path'], error)
        assert np.isfinite(world).all()
        for sub in mesh['submeshes']:
            indices = np.frombuffer(binary, '<i4', sub['count'], sub['offset'])
            assert indices.min() >= 0 and indices.max() < mesh['vertexCount']
    # CastleExterior-specific provenance checks do not apply to ArenaScene or
    # the packed NewScene export, which legitimately have no TreeB material.
    if 'CastleExterior' in folder.name:
        tree = next(m for m in d['materials'] if 'TreeB' in m['name'])
        assert tree['textureProperty'] == '_MainTexture' and 'TreeB_C' in tree['texturePath']
        land = next(o for o in d['objects'] if o['path'].endswith('/CastleExterior_Land'))
        assert 130 < land['boundsSize']['x'] < 145 and 175 < land['boundsSize']['z'] < 190
    results[folder.name] = dict(objects=len(d['objects']), meshes=len(d['meshes']), materials=len(d['materials']), maximumWorldBoundsError=max_error, checks='PASS')
(root/'validation.json').write_text(json.dumps(results, indent=2))
print(json.dumps(results, indent=2))
