// Researcher isolation only. Preserve native React plugin/settings, change runtime ports.
import {fileURLToPath} from 'node:url';
import config from '../../frontend/vite.config.ts';
export default {...config,root:fileURLToPath(new URL('../../frontend/',import.meta.url)),server:{host:'127.0.0.1',port:5174,strictPort:true,proxy:{'/api':{target:'http://127.0.0.1:8020',changeOrigin:true}}}};
