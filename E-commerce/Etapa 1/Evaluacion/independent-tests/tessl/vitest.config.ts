import path from 'node:path';

const frontendRoot = path.resolve(__dirname, '../../../Tessl/frontend');
const testRunnerRoot = path.resolve(__dirname, '../../../Bmad Method/frontend');
const testModules = path.resolve(testRunnerRoot, 'node_modules');
const frontendCoverageGlob = `${frontendRoot.replace(/\\/g, '/')}/src/**/*.{ts,tsx}`;

export default {
  // Keep the test runner rooted where the independent test dependencies are
  // installed. Production files are imported read-only from Tessl.
  root: testRunnerRoot,
  resolve: {
    alias: {
      react: path.resolve(testModules, 'react'),
      'react-dom': path.resolve(testModules, 'react-dom'),
      '@testing-library/react': path.resolve(testModules, '@testing-library/react/dist/index.js'),
      '@testing-library/user-event': path.resolve(testModules, '@testing-library/user-event/dist/esm/index.js'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: [path.resolve(testModules, '@testing-library/jest-dom/dist/vitest.mjs')],
    include: ['../../Evaluacion/independent-tests/tessl/frontend.test.tsx'],
    coverage: {
      provider: 'v8',
      allowExternal: true,
      all: true,
      reporter: ['text', 'json-summary', 'lcov'],
      reportsDirectory: path.resolve(__dirname, 'coverage-frontend'),
      include: [frontendCoverageGlob],
    },
  },
};
