import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import App from '../../../Tessl/frontend/src/App';
import { AppProvider, useApp } from '../../../Tessl/frontend/src/context/AppContext';


const products = [
  { id: 1, name: 'Keyboard', image_url: 'keyboard.jpg', description: 'Ergonomic keyboard', price: 129.99, availability: true },
  { id: 5, name: 'Backpack', image_url: 'backpack.jpg', description: 'Canvas backpack', price: 59.99, availability: false },
];

const jsonResponse = (body: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));

function ContextProbe() {
  const app = useApp();
  return (
    <div>
      <span data-testid="view">{app.view}</span>
      <span data-testid="cart-size">{app.cart.length}</span>
      <button onClick={() => app.setView('checkout')}>guard checkout</button>
      <button onClick={() => app.addToCart(products[0])}>add available</button>
      <button onClick={() => app.addToCart(products[1])}>add unavailable</button>
      <button onClick={() => app.updateQuantity(1, 0)}>invalid quantity</button>
      <button onClick={() => app.removeFromCart(999)}>remove missing</button>
      <button onClick={() => app.setCheckoutRedirectIntent(true)}>set redirect</button>
      <button onClick={() => void app.login('probe', 'secret')}>login</button>
      <button onClick={() => void app.register('probe', 'secret')}>register</button>
      <button onClick={() => void app.checkout()}>checkout</button>
      <button onClick={() => void app.logout()}>logout</button>
      <span data-testid="feedback">{app.feedback?.text ?? ''}</span>
    </div>
  );
}

describe('Tessl Stage 1 independent frontend coverage', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/api/products')) return jsonResponse(products);
      if (url.endsWith('/api/register')) {
        const body = JSON.parse(String(init?.body));
        return jsonResponse({ username: body.username, token: 'register-token' });
      }
      if (url.endsWith('/api/login')) {
        const body = JSON.parse(String(init?.body));
        if (body.password === 'wrong') return jsonResponse({ detail: 'Invalid username or password' }, 401);
        return jsonResponse({ username: body.username, token: 'login-token' });
      }
      if (url.endsWith('/api/logout')) return jsonResponse({ message: 'Logged out' });
      if (url.endsWith('/api/checkout')) {
        return jsonResponse({ summary: { items: [{ product_id: 1, name: 'Keyboard', price: 129.99, quantity: 1, item_total: 129.99 }], total_amount: 129.99, buyer: 'frontend-user' } });
      }
      return jsonResponse({ detail: 'Unexpected request' }, 500);
    }));
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it('completes the visitor, cart, authentication, checkout, and confirmation journey', async () => {
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByText('Keyboard')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Add Backpack to cart' })).toBeDisabled();
    fireEvent.error(screen.getByAltText('Keyboard'));
    expect(screen.getByText('Image Unavailable')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Add Keyboard to cart' }));
    await user.click(screen.getByRole('button', { name: 'Add Keyboard to cart' }));
    await user.click(screen.getByRole('button', { name: /^Cart/ }));
    expect(screen.getAllByText('$259.98')).toHaveLength(2);
    await user.click(screen.getByRole('button', { name: 'Decrease quantity of Keyboard' }));
    await user.click(screen.getByRole('button', { name: 'Increase quantity of Keyboard' }));
    await user.click(screen.getByRole('button', { name: 'Proceed to checkout summary' }));
    expect(screen.getByText('Please sign in or register to complete your checkout.')).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: 'Register' }));
    await user.type(screen.getByLabelText('Username'), 'frontend-user');
    await user.type(screen.getByLabelText('Password'), 'secret');
    await user.click(screen.getAllByRole('button', { name: 'Register', exact: true }).at(-1)!);
    expect(await screen.findByText('Simulated Checkout')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Confirm Simulated Purchase' }));
    expect(await screen.findByText('Simulated Purchase Confirmed!')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Start New Purchase' }));
    expect(await screen.findByText('Product Catalog')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Sign Out' }));
    expect(await screen.findByText('Not Signed In')).toBeInTheDocument();
  });

  it('covers empty cart, removal, navigation, validation, and failed login', async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText('Keyboard');
    await user.click(screen.getByRole('button', { name: /^Cart/ }));
    expect(screen.getByText('Your Shopping Cart is Empty')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Go to Catalog' }));
    await user.click(screen.getByRole('button', { name: 'Add Keyboard to cart' }));
    await user.click(screen.getByRole('button', { name: /^Cart/ }));
    await user.click(screen.getByRole('button', { name: 'Remove Keyboard from cart' }));
    expect(screen.getByText('Your Shopping Cart is Empty')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Sign In' }));
    await user.click(screen.getAllByRole('button', { name: 'Sign In', exact: true }).at(-1)!);
    expect(screen.getByRole('alert')).toHaveTextContent('Username is required.');
    await user.type(screen.getByLabelText('Username'), 'frontend-user');
    await user.click(screen.getAllByRole('button', { name: 'Sign In', exact: true }).at(-1)!);
    expect(screen.getByRole('alert')).toHaveTextContent('Password is required.');
    await user.type(screen.getByLabelText('Password'), 'wrong');
    await user.click(screen.getAllByRole('button', { name: 'Sign In', exact: true }).at(-1)!);
    expect(await screen.findByText('Invalid username or password')).toBeInTheDocument();
  });

  it('covers catalog fetch failure and lower-level context guard branches', async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new Error('Catalog unavailable'));
    const user = userEvent.setup();
    render(<AppProvider><ContextProbe /></AppProvider>);
    expect(await screen.findByTestId('feedback')).toHaveTextContent('Catalog unavailable');
    await user.click(screen.getByText('guard checkout'));
    expect(screen.getByTestId('feedback')).toHaveTextContent('empty');
    await user.click(screen.getByText('add unavailable'));
    expect(screen.getByTestId('feedback')).toHaveTextContent('out of stock');
    await user.click(screen.getByText('invalid quantity'));
    await user.click(screen.getByText('remove missing'));
    await user.click(screen.getByRole('button', { name: 'checkout', exact: true }));
    expect(screen.getByTestId('feedback')).toHaveTextContent('Authentication is required');
    await user.click(screen.getByText('logout'));

    await user.click(screen.getByText('add available'));
    await user.click(screen.getByText('set redirect'));
    await user.click(screen.getByText('login'));
    await waitFor(() => expect(screen.getByTestId('view')).toHaveTextContent('checkout'));
    await user.click(screen.getByRole('button', { name: 'checkout', exact: true }));
    await waitFor(() => expect(screen.getByTestId('view')).toHaveTextContent('confirmation'));
  });

  it('rejects useApp outside the provider', () => {
    const BadConsumer = () => { useApp(); return null; };
    expect(() => render(<BadConsumer />)).toThrow('useApp must be used within an AppProvider');
  });

  it('boots the production entry point', async () => {
    document.body.innerHTML = '<div id="root"></div>';
    await import('../../../Tessl/frontend/src/main');
    await waitFor(() => expect(document.getElementById('root')).toHaveTextContent('E-Commerce Demo'));
  });
});
