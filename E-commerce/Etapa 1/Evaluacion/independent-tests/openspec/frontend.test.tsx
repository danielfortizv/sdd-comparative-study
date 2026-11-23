import React from 'react';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import App from './frozen-first-implementation/frontend/src/App';

const products = [{
  id: 1,
  name: 'Academic Headphones',
  description: 'Demonstration product',
  price: 59.99,
  is_available: true,
  image_url: 'https://example.invalid/product.png',
}];

const jsonResponse = (body: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  }));

describe('OpenSpec frozen first implementation', () => {
  beforeEach(() => {
    window.history.replaceState({}, '', '/');
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/api/products')) return jsonResponse(products);
      if (url.endsWith('/api/auth/register')) return jsonResponse({ id: 1, account_identifier: 'student' }, 201);
      if (url.endsWith('/api/auth/login')) {
        const body = JSON.parse(String(init?.body));
        if (body.password === 'wrong') return jsonResponse({ detail: 'Invalid credentials.' }, 401);
        return jsonResponse({ access_token: 'academic-token', token_type: 'bearer', account_identifier: body.account_identifier });
      }
      return jsonResponse({ detail: 'Unexpected request' }, 500);
    }));
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it('covers the complete initial visitor journey including its acknowledgment blocker', async () => {
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByText('Academic Headphones')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /add academic headphones.*shopping cart/i }));
    await user.click(screen.getAllByRole('link', { name: /shopping cart/i })[0]);
    await user.click(screen.getByRole('button', { name: /increase quantity/i }));
    await user.click(screen.getByRole('button', { name: /decrease quantity/i }));
    await user.click(screen.getByRole('button', { name: /proceed to simulated checkout/i }));
    expect(await screen.findByText(/cart has been preserved/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /switch to register/i }));
    await user.type(screen.getByLabelText(/Account Identifier/), 'student');
    await user.type(screen.getByLabelText(/Password/), 'secret');
    await user.click(screen.getByRole('button', { name: /submit registration/i }));
    expect(await screen.findByText(/registration successful/i)).toBeInTheDocument();
    await user.type(screen.getByLabelText(/Password/), 'secret');
    await user.click(screen.getByRole('button', { name: /submit sign in/i }));
    expect(await screen.findByText('Simulated Checkout Summary')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /confirm purchase/i }));
    expect(screen.getByRole('alert')).toHaveTextContent(/acknowledgment checkbox/i);
    await user.click(screen.getByLabelText(/I acknowledge that this is a simulated purchase/i));
    await user.click(screen.getByRole('button', { name: /confirm purchase/i }));
    expect(await screen.findByText(/Purchase Confirmed/i)).toBeInTheDocument();
    expect(screen.getByText(/\*\*No real charges/)).toBeInTheDocument();
  });

  it('covers validation and recoverable catalog states', async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockRejectedValueOnce(new Error('offline'));
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByText('Connection Error')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /retry loading/i }));
    expect(await screen.findByText('Academic Headphones')).toBeInTheDocument();
    await user.click(screen.getByRole('link', { name: /sign in/i }));
    await user.click(screen.getByRole('button', { name: /submit sign in/i }));
    expect(screen.getByText('Account identifier is required.')).toBeInTheDocument();
    await user.type(screen.getByLabelText(/Account Identifier/), 'student');
    await user.type(screen.getByLabelText(/Password/), 'wrong');
    await user.click(screen.getByRole('button', { name: /submit sign in/i }));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Invalid credentials.'));
  });
});
