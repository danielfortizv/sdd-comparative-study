import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    coverage: {
      provider: 'v8',
      reporter: ['lcov', 'text'],
      all: true,
      include: ['src/**/*'],
      exclude: [
        'src/styles.css',
        'src/App.test.tsx',
        'src/main.test.tsx',
        '**/*.d.ts'
      ],
    },
  },
})
