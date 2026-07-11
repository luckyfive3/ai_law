import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/frontend-unit/setup.js'],
    testTimeout: 5000,
  },
});
