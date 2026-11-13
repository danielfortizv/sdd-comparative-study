import { describe, it, expect } from 'vitest';

interface Product {
  id: number;
  name: string;
  price: number;
  availability: boolean;
}

interface CartItem {
  product: Product;
  quantity: number;
}

function calculateTotal(cart: CartItem[]): number {
  const sum = cart.reduce((total, item) => total + item.product.price * item.quantity, 0);
  return Math.round(sum * 100) / 100;
}

describe('Frontend Cart Math Utils', () => {
  it('should calculate the total purchase amount correctly', () => {
    const mockProduct1: Product = {
      id: 1,
      name: 'Premium Ergonomic Keyboard',
      price: 129.99,
      availability: true,
    };
    const mockProduct2: Product = {
      id: 2,
      name: 'Wireless Optical Mouse',
      price: 49.99,
      availability: true,
    };

    const cart: CartItem[] = [
      { product: mockProduct1, quantity: 2 },
      { product: mockProduct2, quantity: 1 },
    ];

    const total = calculateTotal(cart);
    expect(total).toBe(309.97); // 129.99 * 2 + 49.99 = 259.98 + 49.99 = 309.97
  });

  it('should return 0 for an empty cart', () => {
    const total = calculateTotal([]);
    expect(total).toBe(0);
  });
});
