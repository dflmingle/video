"""Read-only source provenance and prefab restoration audit; no production imports.
Run: python tools/test_scene_sources_v22.py --source-root ../PveMontageShot01V22
JSON includes unresolved bindings and scene-vs-prefab placement; nonzero on defects.
"""
from pathlib import Path
import argparse, collections, hashlib, json, re, tarfile
import numpy as np
import yaml
from scipy.spatial.transform import Rotation

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""): h.update(chunk)
    return h.hexdigest()

def blocks(path):
    return {int(i): (int(t), next(iter(yaml.safe_load(v).values())))
            for t, i, v in re.findall(r"--- !u!(\d+) &(-?\d+)[^\n]*\n(.*?)(?=\n--- !u!|\Z)", path.read_text(encoding="utf8"), re.S)}

def trs(data, edits=None):
    fields = {"m_LocalPosition": dict(x=0,y=0,z=0),
              "m_LocalRotation": dict(x=0,y=0,z=0,w=1),
              "m_LocalScale": dict(x=1,y=1,z=1)}
    for k in fields: fields[k].update(data.get(k, {}))
    for key, value in (edits or {}).items():
        if "." in key:
            a,b=key.split(".",1)
            if a in fields and b in fields[a]: fields[a][b]=float(value)
    p,q,s=(fields[x] for x in fields)
    m=np.eye(4); m[:3,:3]=Rotation.from_quat([q[k] for k in "xyzw"]).as_matrix() @ np.diag([s[k] for k in "xyz"])
    m[:3,3]=[p[k] for k in "xyz"]
    return m

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--source-root",type=Path,default=Path(__file__).resolve().parents[1]); ap.add_argument("--output",type=Path,default=Path(__file__).resolve().parents[1]/"output/v22-scene-source-audit/result.json")
    args=ap.parse_args(); root=args.source_root.resolve(); asset=root/"assets/imported"
    missing=[str(root/f"docs/v22-scenes/{name}.json") for name in ["CastleExterior","ArenaScene"] if not (root/f"docs/v22-scenes/{name}.json").is_file()]
    if missing:
        result=dict(status="BLOCKED_MISSING_INPUT",missing=missing,passed=False,
                    reason="Historical prefab conversion manifests are absent; native export checks are separate and do not make this test pass.")
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2),encoding="utf8")
        print(json.dumps(result));return 2
    inv=json.loads((root/"docs/package-inventory.json").read_text(encoding="utf8")); by_guid={x["guid"]:x for x in inv}; by_path={x["original"]:x for x in inv}
    provenance=json.loads((root/"docs/input-provenance.json").read_text(encoding="utf8"))
    result=dict(sourceRoot=str(root),provenance=[],scenes={},failures=[],warnings=[])
    selected=set(); shaders=set(); materials={}
    def require(ok,message):
        if not ok: result["failures"].append(message)
    for path, expected in provenance.items():
        p=Path(path); actual=dict(path=path,exists=p.exists())
        if p.exists(): actual.update(bytes=p.stat().st_size,sha256=sha(p))
        actual["match"]=actual.get("bytes")==expected["bytes"] and actual.get("sha256")==expected["sha256"]
        result["provenance"].append(actual); require(actual["match"],f"Original input changed/missing: {p.name}")
    def url_path(url): return asset/url.removeprefix("/assets/imported/")
    def original(path): return path.relative_to(asset).as_posix()
    def mark(path):
        name=original(path); selected.add(name); entry=by_path.get(name)
        require(entry is not None,f"Not in package inventory: {name}")
        if entry:
            require(path.exists(),f"Source file missing: {name}")
            if path.exists() and entry.get("sha256"): require(sha(path)==entry["sha256"],f"Inventory SHA mismatch: {name}")
            meta=Path(str(path)+".meta")
            if meta.exists():
                d=yaml.safe_load(meta.read_text(encoding="utf8")); require(d.get("guid")==entry["guid"],f"Meta GUID mismatch: {name}")
        return entry
    def inspect_mat(path):
        if str(path) in materials:return materials[str(path)]
        mark(path); d=next(v for t,v in blocks(path).values() if t==21); shader=d.get("m_Shader",{}).get("guid"); shaders.add(shader)
        slots={k:v for x in d.get("m_SavedProperties",{}).get("m_TexEnvs",[]) for k,v in x.items()}; bindings={}
        for key,value in slots.items():
            g=value.get("m_Texture",{}).get("guid")
            if g in by_guid:
                tex=asset/by_guid[g]["original"]; mark(tex); bindings[key]=dict(guid=g,path=original(tex),sha256=sha(tex))
        out=dict(source=original(path),shaderGUID=shader,bindings=bindings); materials[str(path)]=out; return out
    def expand(path,parent=None,edits=None):
        # Independent transform accumulation. Edits are keyed by source target fileID.
        parent=np.eye(4) if parent is None else parent
        if path.suffix.lower()==".fbx":
            # FBX prefab transform modifications target imported root Transform.
            local={k:v for fields in (edits or {}).values() for k,v in fields.items()}
            return [(original(path),parent@trs({},local))]
        mark(path); docs=blocks(path); trans={i:d for i,(t,d) in docs.items() if t==4 and "m_LocalPosition" in d}; cache={0:parent}
        def world(i):
            if i not in cache:
                d=trans[i]; cache[i]=world(d["m_Father"]["fileID"])@trs(d,(edits or {}).get(i))
            return cache[i]
        out=[]
        for _,(typ,d) in docs.items():
            if typ!=1001:continue
            g=d["m_SourcePrefab"]["guid"]; src=asset/by_guid[g]["original"]; changes=collections.defaultdict(dict)
            for x in d["m_Modification"]["m_Modifications"]:
                if x["propertyPath"].startswith(("m_LocalPosition.","m_LocalRotation.","m_LocalScale.")):
                    changes[x["target"]["fileID"]][x["propertyPath"]]=x.get("value")
            parent_id=d["m_Modification"]["m_TransformParent"]["fileID"]
            out+=expand(src,world(parent_id),changes)
        return out
    for name in ["CastleExterior","ArenaScene"]:
        data=json.loads((root/f"docs/v22-scenes/{name}.json").read_text(encoding="utf8")); prefab=url_path(data["sourcePrefab"]); mark(prefab)
        require(sha(prefab)==data["sourceSHA256"],f"{name}: prefab SHA mismatch")
        scene=prefab.with_name(name+".unity"); mark(scene); pre_guid=by_path[original(prefab)]["guid"]
        placements=[]
        for _,(typ,d) in blocks(scene).items():
            if typ==1001 and d.get("m_SourcePrefab",{}).get("guid")==pre_guid:
                placements.extend(dict(targetFileID=x["target"]["fileID"],property=x["propertyPath"],value=x.get("value")) for x in d["m_Modification"]["m_Modifications"] if x["propertyPath"].startswith(("m_LocalPosition.","m_LocalRotation.","m_LocalScale.")))
        expected=expand(prefab); actual=data["objects"]; require(len(expected)==len(actual),f"{name}: prefab instance count mismatch")
        errors=[]; matrix_differences=[]; bindings=[]; model_names=collections.Counter()
        for index,o in enumerate(actual):
            model=url_path(o["model"]); mark(model); model_names[model.name]+=1
            require(o["sha256"]==sha(model),f"{name}: model SHA mismatch {model.name}")
            if index<len(expected):
                exp_path,matrix=expected[index]; require(exp_path==original(model),f"{name}: model order mismatch {index}")
                actual_matrix=np.array(o["matrix"]).reshape(4,4).T
                error=float(np.max(np.abs(matrix-actual_matrix))); errors.append(error)
                if error>1e-7: matrix_differences.append(dict(index=index,model=model.name,maxError=error,expectedPosition=matrix[:3,3].tolist(),actualPosition=actual_matrix[:3,3].tolist()))
            meta=yaml.safe_load(Path(str(model)+".meta").read_text(encoding="utf8")); importer=meta.get("ModelImporter",{}); external={x["first"]["name"]:x["second"].get("guid") for x in importer.get("externalObjects",[])}
            for slot,mat in o["materials"].items():
                mp=url_path(mat["source"]); info=inspect_mat(mp); bindings.append(dict(model=model.name,slot=slot,material=info["source"],texture=mat.get("texture"),shaderGUID=info["shaderGUID"]))
                if slot in external:
                    g=external[slot]
                    if g in by_guid and by_guid[g]["original"]!=info["source"]:
                        result["warnings"].append(f"Renderer override needs review: {model.name}:{slot}")
        require(not errors or max(errors)<1e-7,f"{name}: prefab matrix error {max(errors) if errors else None}")
        result["scenes"][name]=dict(instances=len(actual),models=dict(model_names),uniqueModels=len(model_names),uniqueMaterials=len(set(x["material"] for x in bindings)),matrixMaxError=max(errors,default=0),matrixDifferences=matrix_differences,unitySceneOverrides=placements,bindings=bindings,sourcePrefab=original(prefab),sourceScene=original(scene))
    # Original tar members, not the extracted copies, establish package membership.
    package=next(Path(p) for p in provenance if p.endswith(".unitypackage")); wanted={by_path[p]["guid"]:p for p in selected}; shader_source={}; seen=set(); checked=0
    with tarfile.open(package,"r|gz") as tf:
        for member in tf:
            parts=member.name.split("/")
            if len(parts)!=2:continue
            guid,kind=parts
            if guid in shaders and kind=="asset": shader_source[guid]=tf.extractfile(member).read().decode("utf8",errors="replace")
            if guid not in wanted:continue
            if kind=="pathname":
                got=tf.extractfile(member).read().decode("utf8").strip(); require(got==wanted[guid],f"Package pathname mismatch: {wanted[guid]}")
            elif kind=="asset":
                h=hashlib.sha256()
                f=tf.extractfile(member)
                for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
                require(h.hexdigest()==sha(asset/wanted[guid]),f"Original package bytes mismatch: {wanted[guid]}"); seen.add(guid); checked+=1
            elif kind=="asset.meta":
                raw=tf.extractfile(member).read(); local=Path(str(asset/wanted[guid])+".meta")
                require(local.exists() and hashlib.sha256(raw).hexdigest()==sha(local),f"Original meta bytes mismatch: {wanted[guid]}")
    require(set(wanted)<=seen,"Some referenced source files absent from original package")
    result["packageAssetsChecked"]=checked; result["materials"]=list(materials.values())
    for scene in result["scenes"].values():
        for row in scene["bindings"]:
            material=next(m for m in result["materials"] if m["source"]==row["material"]); source=shader_source.get(row["shaderGUID"],"")
            used=[slot for slot in material["bindings"] if re.search(r"tex2D(?:lod)?\s*\(\s*"+re.escape(slot)+r"\b",source)]
            # Only base/albedo slots; AO, noise and matcap remain separate shader inputs.
            base=[s for s in used if s in ["_MainTexture","_MainTex","_BaseMap"]]
            row["shaderSampledBaseSlots"]=base
            if len(base)==1:
                expected="/assets/imported/"+material["bindings"][base[0]]["path"]
                require(row["texture"]==expected,f"Shader base texture mismatch: {row['material']} expected {base[0]}")
            elif not base:
                candidates={v["path"] for k,v in material["bindings"].items() if k in ["_BaseMap","_MainTex","_MainTexture"]}
                if row["shaderGUID"]=="0000000000000000f000000000000000" and len(candidates)==1:
                    expected="/assets/imported/"+next(iter(candidates))
                    row["bindingEvidence"]="Built-in shader; all populated base slots agree"
                    require(row["texture"]==expected,f"Built-in shader base texture mismatch: {row['material']}")
                else: result["warnings"].append(f"No supported sampled base slot resolved: {row['material']}")
    result["failures"]=list(dict.fromkeys(result["failures"])); result["warnings"]=list(dict.fromkeys(result["warnings"])); result["passed"]=not result["failures"]
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
    print(json.dumps(dict(passed=result["passed"],packageAssetsChecked=checked,failures=result["failures"],warnings=result["warnings"],output=str(args.output)),ensure_ascii=True,indent=2)); return 0 if result["passed"] else 1

if __name__=="__main__": raise SystemExit(main())
