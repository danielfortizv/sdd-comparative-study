// Researcher runtime proxy for isolated browser fixtures. Production config unchanged.
import {fileURLToPath} from 'node:url';
import {mergeConfig} from '../../frontend/node_modules/vite/dist/node/index.js';
import productionConfig from '../../frontend/vite.config.ts';
export default mergeConfig(productionConfig,{
 root:fileURLToPath(new URL('../../frontend/',import.meta.url)),
 server:{host:'127.0.0.1',port:3001,strictPort:true,proxy:{'/api':{target:'http://127.0.0.1:8011',changeOrigin:true}}}
});
