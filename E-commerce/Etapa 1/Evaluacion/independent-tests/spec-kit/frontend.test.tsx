import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import App from '../../../Spec Kit/frontend/src/App';
import { AuthProvider, useAuth } from '../../../Spec Kit/frontend/src/context/AuthContext';
import { CartProvider, useCart } from '../../../Spec Kit/frontend/src/context/CartContext';
import { ToastProvider, useToast } from '../../../Spec Kit/frontend/src/components/FeedbackToast';
import { ErrorFallback } from '../../../Spec Kit/frontend/src/components/StateFallbacks';


const products = [{
  product_id: 'prod-001',
  name: 'Keyboard',
  representative_image: 'keyboard.jpg',
  short_description: 'Ergonomic keyboard',
  price: 129.99,
  general_availability: 'Available',
}];

const jsonResponse = (body: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));

function GuardProbe() {
  const auth = useAuth();
  const cart = useCart();
  const toast = useToast();
  return <div>
    <span data-testid="auth-state">{String(auth.isAuthenticated)}</span>
    <span data-testid="cart-size">{cart.items.length}</span>
    <span data-testid="cart-total">{cart.accumulated_total}</span>
    <button onClick={() => cart.addItem(products[0])}>add</button>
    <button onClick={() => cart.updateQuantity('prod-001', 3)}>set three</button>
    <button onClick={() => cart.updateQuantity('prod-001', 0)}>set zero</button>
    <button onClick={() => cart.removeItem('missing')}>remove missing</button>
    <button onClick={() => cart.clearCart()}>clear</button>
    <button onClick={() => toast.showToast('probe')}>toast</button>
    <button onClick={() => void auth.signOut()}>signout</button>
  </div>;
}

describe('Spec Kit Stage 1 independent frontend coverage', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/api/products')) return jsonResponse(products);
      if (url.endsWith('/api/register')) return jsonResponse({ message: 'Account successfully registered.' }, 201);
      if (url.endsWith('/api/signin')) {
        const body = JSON.parse(String(init?.body));
        if (body.password === 'wrong') return jsonResponse({ error: 'Invalid identifier or password.' }, 401);
        return jsonResponse({ session_token: 'token-1' });
      }
      if (url.endsWith('/api/signout')) return jsonResponse({ message: 'Session successfully terminated.' });
      if (url.endsWith('/api/checkout')) return jsonResponse({
        message: 'Simulated purchase confirmed! No real payment gateway was contacted.',
        purchase_summary: { items: [{ product_id: 'prod-001', name: 'Keyboard', quantity: 1, unit_price: 129.99, subtotal: 129.99 }], accumulated_total: 129.99 },
      });
      return jsonResponse({ error: 'Unexpected request' }, 500);
    }));
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('completes catalog, cart, registration, sign-in, checkout, confirmation and sign-out', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<App />);
    expect(await screen.findByText('Keyboard')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Add Keyboard to cart' }));
    await user.click(screen.getByRole('button', { name: 'Increase quantity of Keyboard' }));
    await user.click(screen.getByRole('button', { name: 'Decrease quantity of Keyboard' }));
    fireEvent.change(screen.getByLabelText('Quantity of Keyboard'), { target: { value: '2' } });
    await user.click(screen.getByRole('button', { name: 'Proceed to Checkout' }));
    expect(screen.getByTestId('signin-form')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Register' }));
    await user.click(screen.getByRole('button', { name: 'Register Account' }));
    expect(screen.getByText('Please fill in all expected information.')).toBeInTheDocument();
    await user.type(screen.getByLabelText('Customer Identification (Identifier)'), 'student');
    await user.type(screen.getByLabelText('Secure Password'), 'secret');
    await user.click(screen.getByRole('button', { name: 'Register Account' }));
    expect(await screen.findByTestId('signin-form')).toBeInTheDocument();
    await user.type(screen.getByLabelText('Customer Identification (Identifier)'), 'student');
    await user.type(screen.getByLabelText('Password'), 'secret');
    await user.click(screen.getAllByRole('button', { name: 'Sign In' }).at(-1)!);
    expect(await screen.findByTestId('checkout-page')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Confirm Simulated Purchase' }));
    expect(screen.getByText('Please fill in the minimum requested demonstration information.')).toBeInTheDocument();
    await user.type(screen.getByLabelText(/Detail A/), 'A');
    await user.type(screen.getByLabelText(/Detail B/), 'B');
    await user.click(screen.getByRole('button', { name: 'Confirm Simulated Purchase' }));
    expect(await screen.findByText('Simulated Purchase Confirmed!')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Start New Simulated Purchase Journey' }));
    expect(await screen.findByText('Product Catalog')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Sign Out' }));
    expect(await screen.findByText('Guest Visitor')).toBeInTheDocument();
  });

  it('covers failed catalog retry, empty catalog, auth cancellation and invalid sign-in', async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new Error('Catalog unavailable'));
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<App />);
    expect(await screen.findByText('Catalog unavailable')).toBeInTheDocument();
    vi.mocked(fetch).mockResolvedValueOnce(await jsonResponse([]));
    await user.click(screen.getByRole('button', { name: 'Retry Action' }));
    expect(await screen.findByText(/No products are currently available/)).toBeInTheDocument();
    cleanup();
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/api/products')) return jsonResponse(products);
      if (url.endsWith('/api/signin')) return jsonResponse({ error: 'Invalid identifier or password.' }, 401);
      return jsonResponse({});
    });
    render(<App />);
    await screen.findByText('Keyboard');
    await user.click(screen.getByRole('button', { name: 'Add Keyboard to cart' }));
    await user.click(screen.getByRole('button', { name: 'Proceed to Checkout' }));
    await user.click(screen.getAllByRole('button', { name: 'Sign In' }).at(-1)!);
    expect(screen.getByText('Please enter your identification and password.')).toBeInTheDocument();
    await user.type(screen.getByLabelText('Customer Identification (Identifier)'), 'student');
    await user.type(screen.getByLabelText('Password'), 'wrong');
    await user.click(screen.getAllByRole('button', { name: 'Sign In' }).at(-1)!);
    expect(await screen.findByText('Invalid identifier or password.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByTestId('signin-form')).not.toBeInTheDocument();
  });

  it('covers context state branches, toast expiry, and fallback controls', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<ToastProvider><AuthProvider><CartProvider><GuardProbe /></CartProvider></AuthProvider></ToastProvider>);
    await user.click(screen.getByText('add'));
    await user.click(screen.getByText('add'));
    await user.click(screen.getByText('set three'));
    expect(screen.getByTestId('cart-total')).toHaveTextContent('389.97');
    await user.click(screen.getByText('remove missing'));
    await user.click(screen.getByText('set zero'));
    expect(screen.getByTestId('cart-size')).toHaveTextContent('0');
    await user.click(screen.getByText('clear'));
    await user.click(screen.getByText('signout'));
    await user.click(screen.getByText('toast'));
    expect(screen.getByTestId('feedback-toast')).toHaveTextContent('probe');
    vi.advanceTimersByTime(4000);
    await waitFor(() => expect(screen.queryByTestId('feedback-toast')).not.toBeInTheDocument());
    cleanup();
    const retry = vi.fn();
    render(<ErrorFallback message="failure" onRetry={retry} />);
    await user.click(screen.getByRole('button', { name: 'Retry Action' }));
    expect(retry).toHaveBeenCalled();
  });

  it('rejects all custom hooks outside their providers', () => {
    const BadAuth = () => { useAuth(); return null; };
    const BadCart = () => { useCart(); return null; };
    const BadToast = () => { useToast(); return null; };
    expect(() => render(<BadAuth />)).toThrow('useAuth must be used within an AuthProvider');
    expect(() => render(<BadCart />)).toThrow('useCart must be used within a CartProvider');
    expect(() => render(<BadToast />)).toThrow('useToast must be used within a ToastProvider');
  });

  it('boots the production entry point', async () => {
    document.body.innerHTML = '<div id="root"></div>';
    await import('../../../Spec Kit/frontend/src/index');
    await waitFor(() => expect(document.getElementById('root')).toHaveTextContent('Demonstration Store'));
  });
});
