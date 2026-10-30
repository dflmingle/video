from pathlib import Path
P=Path(__file__).resolve().parents[1];p=P/'src/assets-v11.js';s=p.read_text(encoding='utf-8')
s=s.replace('attribute float response; attribute float posture; attribute float gaitScale; attribute float armSwing;', 'attribute vec4 memberPose;')
s=s.replace(')*armSwing;', ')*memberPose.w;').replace('(gaitScale-1.0)', '(memberPose.z-1.0)').replace('transformed.z+=posture*', 'transformed.z+=memberPose.y*').replace('transformed.z-=response*', 'transformed.z-=memberPose.x*').replace('transformed.y-=response*', 'transformed.y-=memberPose.x*')
s=s.replace("geo.setAttribute('armSwing',armSwing);", "const memberPose=new T.InstancedBufferAttribute(new Float32Array(1024*4),4);geo.setAttribute('memberPose',memberPose);geo.setAttribute('armSwing',armSwing);")
s=s.replace('{mesh,hit,response,posture,gaitScale,armSwing,blend,moveWeight,n:0}', '{mesh,hit,response,posture,gaitScale,armSwing,memberPose,blend,moveWeight,n:0}')
p.write_text(s,encoding='utf-8')
p=P/'src/main-camera.js';s=p.read_text(encoding='utf-8')
a=s.index('b.gaitScale.setX(');b=s.index('b.hit.setX(',a)
s=s[:a]+"b.memberPose.setXYZW(b.n,action!=='death'&&i>=nb&&hitAge>=0&&hitAge<C.hitPoseSeconds?Math.sin(Math.PI*hitAge/C.hitPoseSeconds):0,i>=nb&&action==='move'?ctrl[5]:0,i>=nb&&action==='move'?ctrl[3]/C.runStride:1,i>=nb&&action==='move'?ctrl[6]:0);"+s[b:]
s=s.replace('b.armSwing.needsUpdate=true;', 'b.memberPose.needsUpdate=true;')
p.write_text(s,encoding='utf-8')
p=P/'tools/capture_camera.mjs';s=p.read_text();s=s.replace("page.on('pageerror',e=>errors.push(e.message));", "page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&/Shader Error|WebGLProgram|GL_INVALID/.test(m.text()))errors.push(m.text().slice(0,800))});")
p.write_text(s)
