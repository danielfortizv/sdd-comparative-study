import React from 'react';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import App from '../../../Bmad Method/frontend/src/App';


const products = [
  {
    id: 1,
    name: 'Wireless Stereo Headphones',
    description: 'Headphones description',
    price: 59.99,
    availability: 'In Stock',
    image_svg: '<svg viewBox="0 0 10 10"><circle cx="5" cy="5" r="4"/></svg>',
  },
  {
    id: 2,
    name: 'Unavailable Watch',
    description: 'Watch description',
    price: 120,
    availability: 'Out of Stock',
    image_svg: '<svg viewBox="0 0 10 10"><rect width="10" height="10"/></svg>',
  },
];

const jsonResponse = (body: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  }));

describe('BMAD Stage 1 frontend', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/api/products')) return jsonResponse(products);
      if (url.endsWith('/api/register')) {
        return jsonResponse({ success: true, message: 'Registration successful.' }, 201);
      }
      if (url.endsWith('/api/login')) {
        const body = JSON.parse(String(init?.body));
        if (body.password === 'wrong') {
          return jsonResponse({ detail: 'Invalid username or password.' }, 401);
        }
        return jsonResponse({ success: true, username: body.username });
      }
      if (url.endsWith('/api/checkout')) {
        return jsonResponse({
          success: true,
          order_summary: {
            items: [{ id: 1, name: products[0].name, quantity: 1, price: 59.99, subtotal: 59.99 }],
            total: 59.99,
          },
        });
      }
      return jsonResponse({ detail: 'Unexpected request' }, 500);
    }));
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.clearAllTimers();
  });

  it('completes the visitor-to-confirmation journey and preserves the cart', async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findByText(products[0].name)).toBeInTheDocument();
    expect(screen.getByText('$59.99')).toBeInTheDocument();
    const addButtons = screen.getAllByRole('button', { name: 'Add to Cart', exact: true });
    expect(addButtons[0]).toBeEnabled();
    expect(addButtons[1]).toBeDisabled();

    await user.click(addButtons[0]);
    await user.click(screen.getByRole('button', { name: 'Cart (1)' }));
    expect(screen.getByText('Total:').parentElement).toHaveTextContent('$59.99');

    await user.click(screen.getByRole('button', { name: 'Proceed to Checkout' }));
    expect(screen.getByRole('button', { name: 'Cart (1)' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Register' }));
    await user.type(screen.getByLabelText('Username / Identifier'), 'frontend-user');
    await user.type(screen.getByLabelText('Password'), 'frontend-secret');
    await user.click(screen.getByRole('button', { name: 'Create Account' }));

    await user.type(screen.getByLabelText('Password'), 'frontend-secret');
    await user.click(screen.getAllByRole('button', { name: 'Sign In' }).at(-1)!);
    await waitFor(() => expect(screen.getByText(/Session:/)).toHaveTextContent('Active'));
    expect(screen.getByRole('button', { name: 'Cart (1)' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Proceed to Checkout' }));
    expect(screen.getByText(/no real payment gateway is contacted/i)).toBeInTheDocument();
    expect(screen.getByText('Grand Total:').parentElement).toHaveTextContent('$59.99');
    await user.click(screen.getByRole('button', { name: 'Confirm Simulated Purchase' }));
    expect(await screen.findByText('Thank You For Your Simulated Order!')).toBeInTheDocument();
    expect(screen.getByText('Total Simulated Cost:').parentElement).toHaveTextContent('$59.99');

    await user.click(screen.getByRole('button', { name: 'Start New Purchase' }));
    expect(screen.getByRole('button', { name: 'Cart (0)' })).toBeInTheDocument();
  });

  it('shows useful validation and authentication errors', async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText(products[0].name);
    await user.click(screen.getByRole('button', { name: 'Sign In' }));
    await user.click(screen.getAllByRole('button', { name: 'Sign In' }).at(-1)!);
    expect(screen.getByText(/All fields are required/)).toBeInTheDocument();

    await user.type(screen.getByLabelText('Username / Identifier'), 'frontend-user');
    await user.type(screen.getByLabelText('Password'), 'wrong');
    await user.click(screen.getAllByRole('button', { name: 'Sign In' }).at(-1)!);
    expect(await screen.findByText('Invalid username or password.')).toBeInTheDocument();
  });

  it('shows an actionable catalog error and recovers', async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockRejectedValueOnce(new Error('Catalog unavailable'));
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByText('Catalog unavailable')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Retry Connection' }));
    expect(await screen.findByText(products[0].name)).toBeInTheDocument();
  });
});
