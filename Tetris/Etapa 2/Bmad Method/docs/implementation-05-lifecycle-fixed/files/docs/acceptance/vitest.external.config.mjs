// Researcher configuration; generated app/test/dependency files are untouched.
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root=fileURLToPath(new URL('../../',import.meta.url));
const modules=path.join(root,'frontend/node_modules');
export default {
  root,
  esbuild:{jsx:'automatic'},
  resolve:{alias:[
    {find:/^react$/,replacement:path.join(modules,'react/index.js')},
    {find:/^react\/jsx-runtime$/,replacement:path.join(modules,'react/jsx-runtime.js')},
    {find:/^react\/jsx-dev-runtime$/,replacement:path.join(modules,'react/jsx-dev-runtime.js')},
    {find:/^react-dom$/,replacement:path.join(modules,'react-dom/index.js')},
    {find:/^react-dom\/client$/,replacement:path.join(modules,'react-dom/client.js')},
    {find:/^react-dom\/test-utils$/,replacement:path.join(modules,'react-dom/test-utils.js')},
    {find:/^@testing-library\/react$/,replacement:path.join(modules,'@testing-library/react/dist/index.js')},
    {find:/^vitest$/,replacement:path.join(modules,'vitest/dist/index.js')}
  ],dedupe:['react','react-dom']},
  test:{environment:'jsdom',include:['docs/acceptance/*.external.test.tsx'],fileParallelism:false,globals:false,restoreMocks:true}
};
