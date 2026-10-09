import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import App from '../App';

// Smoke test: confirms the test harness (vitest + jsdom + RTL + jest-dom) works.
describe('App', () => {
  it('renders the calculator heading', () => {
    render(<App />);
    expect(
      screen.getByRole('heading', { name: /web calculator/i }),
    ).toBeInTheDocument();
  });
});
