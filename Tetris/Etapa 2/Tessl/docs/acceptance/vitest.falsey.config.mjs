import {fileURLToPath} from 'node:url';
import { defineConfig } from '../../frontend/node_modules/vitest/dist/config.js';
import react from '../../frontend/node_modules/@vitejs/plugin-react/dist/index.js';
export default defineConfig({root:fileURLToPath(new URL('.',import.meta.url)),resolve:{alias:[{find:/^react(?=\/|$)/,replacement:fileURLToPath(new URL('../../frontend/node_modules/react',import.meta.url))},{find:/^react-dom(?=\/|$)/,replacement:fileURLToPath(new URL('../../frontend/node_modules/react-dom',import.meta.url))}]},plugins:[react()],test:{environment:'jsdom',globals:true,include:['falsey.external.test.tsx'],coverage:{enabled:false}}});
