import {build} from 'vite';
await build({build:{outDir:'output/build-v22r',rollupOptions:{input:{v22:'v22.html',native:'scene-native-v22.html'}}}});
