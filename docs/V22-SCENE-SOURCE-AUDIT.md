# V22 formal scene source audit

Date: 2026-10-29. Scope: read-only source verification. No production scene,
converter, battle, camera or renderer files changed.

**V21 uses a hybrid, adapted environment rather than an original complete
scene. CastleExterior is the more likely planning-page candidate, but the
candidate must be shown as an original-prefab static preview for user
confirmation. The visual inference does not establish the linked scene ID.**

## Reproduction and provenance

```powershell
python tools/test_scene_sources_v22.py --source-root C:/Users/89trillion/PveMontageShot01V22
```

The script writes `output/v22-scene-source-audit/result.json` in this worktree.
It only reads source-root; it neither imports nor invokes the writing production
converter. It independently parses Unity YAML, accumulates target-specific
prefab TRS, streams original UnityPackage pathname/asset/asset.meta members,
and reads shader source from the original package. Detected defects return a
nonzero exit code.

Inputs are locked by `docs/input-provenance.json`:

| Input | Bytes | SHA256 |
|---|---:|---|
| Original PVE UnityPackage | 364377842 | 16a1701d9e48baa681d6b0dfd3989a2356d9a9a741dd1413272cad267cde6859 |
| Original planning PDF | 26895055 | ecb52eeaf5891655c699a30ba20ee487c81e432e012c314965fd9f6bee4561a0 |

First audit: both original inputs match. All 71 referenced scene/model/material/
texture files match original package asset bytes; local meta bytes and inventory
GUIDs match. Original package pathname members are checked too. Some shaders
were not extracted into imported assets, so shader evidence is read directly
from its original GUID member in the package.

## V21 environment mismatch: actual code

| Code | Actual adaptation | Consequence |
|---|---|---|
| `src/environment-v11.js:5` | ArenaScene_Land.fbx + ArenaScene_Land_C.png | One Arena floor, not a complete scene |
| `src/environment-v11.js:6` | Every ground vertex uses `setY(i,0)` and recomputed normals | Original terrain relief removed |
| Same line | Fragment mixes sand tint `(.63,.53,.34)` at weight `.58` | Original appearance altered |
| `src/environment-v11.js:7` | scale `(.065,.065,.078)`, position `(0,-.035,-12)` | Nonuniform rescale and relocation |
| `src/environment.js:4` | CastleExterior_Tree_04 + Tree_C, resized to height 4.5 | Trees from a different scene, with authored size |
| `src/environment.js:6` | 18 trees at x=+/-[30.5+(i%3)*1.2], z=-48+floor(i/2)*11, yaw=i*2.4, scale=.65+(i%4)*.13 | Source prefab layout/count/TRS not retained |

Using original models and textures does not mean the original scene is restored.
Replacing only the ground texture cannot repair this hybrid adaptation.

## Source inventory and object mapping

Base: `assets/imported/Assets/ArtOfWar-II_Art/Environment/`.
Scenes and group prefabs are `Feature/{name}/{name}.unity` and
`Feature/{name}/{name}_Grp.prefab`. Models/materials are in `Common/{name}/`.
CastleExterior originally spells its model directory `Modle`; ArenaScene uses
`Model`. Do not silently normalize either to an absent path.

| Category | CastleExterior original group prefab | ArenaScene original group prefab |
|---|---|---|
| Ground | Land x1 | Land x1, FarLand x1, Grass x1, Brick x1, Steps x1 |
| Walls/buildings | Building x1, external slots Castle and Mountain | HighWalls x4, LowWall x4, Castle x2 |
| Gate | No independently referenced Gate FBX; inspect Building visually | No independently referenced Gate FBX |
| Trees/shrubs | Tree_04 x2, Tree_05 x6 | Shurb_01 x8, Shurb_02 x3, LongShrub x1 (original spelling) |
| Stakes/fence | Stakes_01 x6, Stakes_02 x6 | Cage x4; do not assume a cage is a fence |
| Flag | No standalone Flag referenced | Flag x4 |
| Decorations | Flower_03 x8, Arrow x2, SnowBridge_Gird x1 | Grass, Brick, Steps as above |
| Total | 33 instances, 9 distinct FBX, 6 distinct materials | 35 instances, 13 distinct FBX, 9 distinct materials |

Counts are actual prefab references, not invented semantic meshes. Building may
contain integrated wall/gate components, but this audit has not visually loaded
its internals and does not claim an independently detachable gate. The
cross-directory SnowBridge_Gird reference is genuinely in CastleExterior's
prefab and must not be deleted merely because of its name.

CastleExterior group prefab SHA256:
`3156147ce6291b6024427c641d4255a6bfc0af8a2167825f573b20d61b9ab22d`.
Tree_04 FBX SHA256:
`d0c0a726ae2feb85fe2e96b381b1b46b0f71bee4d24c8f40ae2639ebac46d1d0`.

## Planning page 7: evidence and uncertainty

Actually viewed `docs/pdf-page-07.png`. The lower section specifies longitudinal
red/orange/yellow armies, a blue U, and 3x3 subdivisions. Character thumbnails
show grey stone paving, purple-grey walls/towers and green vegetation. This is
visually more consistent with CastleExterior than V21's adapted sand ground.

The page's scene link is:
`https://drive.89trillion.com:5001/d/f/18LIFiPBiOMRrSB1jDWQ4YgHVNy7uKwo`.
The opaque link ID has not been proven to map to CastleExterior. Show original
CastleExterior and ArenaScene static previews for confirmation. Do not call this
visual candidate inference a confirmed scene selection.

## Transform, units and coordinate-system audit

`tools/convert_scene_v22.py` currently declares `_Grp.prefab` as its source; this
is not the same as all `.unity` scene-level placement/settings. CastleExterior's
33 emitted matrices match independent group-prefab accumulation with max error 0.

Example first Tree_04 Unity position: `(29.210001,0,-5.48)`. Rotation and non-unit
scale are significant and must survive; retaining translation alone is wrong.
Matrices are column-major for Three.js. Apply Unity/Three handedness conversion
and FBX centimetres-to-metres once, with a documented ownership boundary.
Importer flags such as globalScale=1, useFileUnits=1, useFileScale=1 and
bakeAxisConversion=0 do not establish that raw FBX numbers are already metres.

CastleExterior.unity's group instance has root identity modifications plus
child target fileID `2487597120072820930` changes: scale.y=.75958157,
scale.z=.90432, position.z=3.33. Preserve target fileIDs. If using group-prefab
instead of scene, explicitly declare that choice; do not conflate them.

First audit found 8 ArenaScene HighWalls/Flag matrix mismatches, max matrix
component error 48.792784. Example index 0 HighWalls independent position is
`(20.982918,0,57.605633381875)`; initial JSON gives `(-.6,9.7,8.81284895)`.
The converter flattens modifications for different target fileIDs into one dict,
then applies them only to prefab roots. Child edits overwrite root edits. The
fix must retain target identity throughout hierarchical expansion.

## Material defect: actual shader sampling wins over legacy properties

Initial `mat()` uses:

```python
m = tex.get('_BaseMap') or tex.get('_MainTex') or {}
```

A `_BaseMap` dict with texture fileID=0 is truthy and prevents fallback, emitting
texture:null. Merely falling back to a valid `_MainTex` GUID is also insufficient:
legacy slots may disagree with the active shader.

Original package GUID `6e46eb022277fe44eb5eeb162a4551b4` resolves to
`Assets/ArtOfWar-II_Art/Shaders/DecShadow.shader`. Its actual line 686 samples
`tex2D(_MainTexture, uv_MainTexture)`. TreeB_Mat demonstrates the difference:

| Slot | Original binding | Meaning |
|---|---|---|
| `_BaseMap` | fileID=0 | Empty |
| `_MainTex` | Tree_C, GUID 7cdc3068e864f0d4383f259084552202 | Legacy field, not active shader base sampling |
| `_MainTexture` | TreeB_C, GUID 9950f7db35dc2d145b1d85c0af66cde8 | Correct active base texture |
| `_RoleAO` | Separate AO texture | Must not replace albedo |

TreeB_C SHA256:
`b11bd365c2a80af237aaec3fb9038c283f9ec1fa035ced68caea94a6f60d587b`.

First run detects 5 CastleExterior and 9 ArenaScene distinct material base-map
mismatches plus the Arena matrix defect: overall FAIL. A defect-finding FAIL is
not a production acceptance PASS. CastleExterior_Land_Mat uses a Unity built-in
shader GUID; its populated `_BaseMap` and `_MainTex` agree on one original image.
The test validates that agreement without pretending to read built-in shader
source from the package.

## Acceptance boundary and remaining work

- Passed initially: original input SHA/bytes; 71 referenced asset/meta/pathname
  records; CastleExterior group-prefab matrices; source and adaptation diagnosis.
- Failed initially: active shader base maps and Arena target-specific TRS.
  Re-run after production fixes; current result.json owns latest status. This
  report retains first-run findings and version context.
- Not covered: final FBXLoader runtime units/handedness/world matrices,
  alpha/cutout/culling and lighting. Those require actual original-scene renders.
- Not done: full-scene static visual confirmation for either candidate. No final
  scene acceptance is claimed.
- No battle was restored or rendered by this audit; no soldier count, army
  position, speed or formation was changed. User approval is still distinct from
  this source audit.
