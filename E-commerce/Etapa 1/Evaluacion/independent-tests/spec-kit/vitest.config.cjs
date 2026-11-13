const path = require('node:path');

const frontendRoot = path.resolve(__dirname, '../../../Spec Kit/frontend');
const runnerRoot = path.resolve(__dirname, '../../../Bmad Method/frontend');
const modules = path.resolve(runnerRoot, 'node_modules');
const coverageGlob = `${frontendRoot.replace(/\\/g, '/')}/src/**/*.{ts,tsx}`;

module.exports = {
  root: runnerRoot,
  resolve: {
    alias: {
      react: path.resolve(modules, 'react'),
      'react-dom': path.resolve(modules, 'react-dom'),
      '@testing-library/react': path.resolve(modules, '@testing-library/react/dist/index.js'),
      '@testing-library/user-event': path.resolve(modules, '@testing-library/user-event/dist/esm/index.js'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: [path.resolve(modules, '@testing-library/jest-dom/dist/vitest.mjs')],
    include: ['../../Evaluacion/independent-tests/spec-kit/frontend.test.tsx'],
    coverage: {
      provider: 'v8',
      allowExternal: true,
      all: true,
      reporter: ['text', 'json-summary', 'lcov'],
      reportsDirectory: path.resolve(__dirname, 'coverage-frontend'),
      include: [coverageGlob],
      exclude: ['**/src/tests/**', '**/setupTests.ts'],
    },
  },
};
