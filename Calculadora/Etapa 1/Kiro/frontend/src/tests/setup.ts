// Vitest setup: registers jest-dom matchers (e.g. toBeInTheDocument), cleans up
// the DOM between tests, and stands up a shared MSW server so no real network
// request escapes the test run.
import '@testing-library/jest-dom/vitest';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { cleanup } from '@testing-library/react';
import { setupServer } from 'msw/node';

// No default handlers: individual tests register their own with
// `server.use(...)`. Any request without a matching handler is an error, so an
// un-mocked network call fails the run instead of hitting a live backend.
export const server = setupServer();

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' });
});

afterEach(() => {
  cleanup();
  server.resetHandlers();
});

afterAll(() => {
  server.close();
});
