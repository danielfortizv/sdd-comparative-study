import path from 'node:path';


const frontendRoot = path.resolve(__dirname, '../../../Bmad Method/frontend');

export default {
  root: frontendRoot,
  resolve: {
    alias: {
      react: path.resolve(frontendRoot, 'node_modules/react'),
      'react-dom': path.resolve(frontendRoot, 'node_modules/react-dom'),
      '@testing-library/react': path.resolve(frontendRoot, 'node_modules/@testing-library/react/dist/index.js'),
      '@testing-library/user-event': path.resolve(frontendRoot, 'node_modules/@testing-library/user-event/dist/esm/index.js'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: [path.resolve(frontendRoot, 'node_modules/@testing-library/jest-dom/dist/vitest.mjs')],
    include: ['../../Evaluacion/independent-tests/bmad/frontend.test.tsx'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json-summary', 'lcov'],
      reportsDirectory: path.resolve(__dirname, 'coverage-frontend'),
      include: ['src/**/*.{ts,tsx}'],
    },
  },
};
