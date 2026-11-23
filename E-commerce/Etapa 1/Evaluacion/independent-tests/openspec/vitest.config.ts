import path from 'node:path';

const evaluationRoot = path.resolve(__dirname);
const frontendRoot = path.resolve(evaluationRoot, 'frozen-first-implementation/frontend');
const runnerRoot = frontendRoot;

export default {
  root: frontendRoot,
  css: { postcss: { plugins: [] } },
  resolve: {
    dedupe: ['react', 'react-dom'],
    alias: {
      react: path.resolve(runnerRoot, 'node_modules/react'),
      'react-dom': path.resolve(runnerRoot, 'node_modules/react-dom'),
      'react-router-dom': path.resolve(runnerRoot, 'node_modules/react-router-dom/dist/index.js'),
      'lucide-react': path.resolve(runnerRoot, 'node_modules/lucide-react/dist/cjs/lucide-react.js'),
      '@testing-library/react': path.resolve(runnerRoot, 'node_modules/@testing-library/react/dist/index.js'),
      '@testing-library/user-event': path.resolve(runnerRoot, 'node_modules/@testing-library/user-event/dist/esm/index.js'),
      '@vitest/coverage-v8': path.resolve(runnerRoot, 'node_modules/@vitest/coverage-v8/dist/index.js'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: [path.resolve(runnerRoot, 'node_modules/@testing-library/jest-dom/dist/vitest.mjs')],
    include: ['../../frontend.test.tsx'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json-summary', 'lcov'],
      reportsDirectory: path.resolve(evaluationRoot, 'coverage-frontend'),
      include: ['src/**/*.{ts,tsx}'],
    },
  },
};
