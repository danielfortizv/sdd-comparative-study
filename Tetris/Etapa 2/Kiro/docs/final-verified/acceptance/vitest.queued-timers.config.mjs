import {fileURLToPath} from 'node:url';
import path from 'node:path';
const here=path.dirname(fileURLToPath(import.meta.url));
const frontend=path.resolve(here,'../../frontend');
export default {root:path.resolve(here,'../..'),resolve:{alias:{
  vitest:path.join(frontend,'node_modules/vitest/dist/index.js'),
  '@testing-library/react':path.join(frontend,'node_modules/@testing-library/react/dist/index.js'),
}},test:{include:['docs/acceptance/queued-timers.external.test.ts'],environment:'jsdom',globals:false,
  pool:'forks',maxWorkers:1,coverage:{enabled:false},testTimeout:5000}};
