import {defineConfig} from 'vite';
export default defineConfig({server:{watch:{ignored:['**/output/**','**/baseline/**','**/variants/**','**/assets/**']}}});
