import React, { createContext, useState, useContext, ReactNode } from 'react';

export interface CartItem {
  id: number;
  name: string;
  price: number;
  quantity: number;
  image_svg: string;
}

interface Product {
  id: number;
  name: string;
  price: number;
  description: string;
  availability: string;
  image_svg: string;
}

interface CartContextType {
  cartItems: CartItem[];
  addToCart: (product: Product) => void;
  updateQuantity: (productId: number, quantity: number) => void;
  removeFromCart: (productId: number) => void;
  clearCart: () => void;
  cartTotal: number;
  cartCount: number;
  cartFeedback: string | null;
  triggerFeedback: (message: string) => void;
}

const CartContext = createContext<CartContextType | undefined>(undefined);

export const CartProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [cartItems, setCartItems] = useState<CartItem[]>([]);
  const [cartFeedback, setCartFeedback] = useState<string | null>(null);

  const triggerFeedback = (message: string) => {
    setCartFeedback(message);
    setTimeout(() => {
      setCartFeedback(null);
    }, 3000);
  };

  const addToCart = (product: Product) => {
    if (product.availability !== "In Stock") {
      triggerFeedback(`"${product.name}" is currently out of stock.`);
      return;
    }

    setCartItems((prevItems) => {
      const existingItem = prevItems.find((item) => item.id === product.id);
      if (existingItem) {
        triggerFeedback(`Increased quantity of ${product.name} in cart.`);
        return prevItems.map((item) =>
          item.id === product.id ? { ...item, quantity: item.quantity + 1 } : item
        );
      }
      triggerFeedback(`Added "${product.name}" to cart.`);
      return [
        ...prevItems,
        {
          id: product.id,
          name: product.name,
          price: product.price,
          quantity: 1,
          image_svg: product.image_svg,
        },
      ];
    });
  };

  const updateQuantity = (productId: number, quantity: number) => {
    if (quantity <= 0) {
      removeFromCart(productId);
      return;
    }
    setCartItems((prevItems) =>
      prevItems.map((item) =>
        item.id === productId ? { ...item, quantity } : item
      )
    );
  };

  const removeFromCart = (productId: number) => {
    const itemToRemove = cartItems.find((item) => item.id === productId);
    if (itemToRemove) {
      triggerFeedback(`Removed "${itemToRemove.name}" from cart.`);
    }
    setCartItems((prevItems) => prevItems.filter((item) => item.id !== productId));
  };

  const clearCart = () => {
    setCartItems([]);
  };

  const cartTotal = cartItems.reduce((acc, item) => acc + item.price * item.quantity, 0);
  const cartCount = cartItems.reduce((acc, item) => acc + item.quantity, 0);

  return (
    <CartContext.Provider
      value={{
        cartItems,
        addToCart,
        updateQuantity,
        removeFromCart,
        clearCart,
        cartTotal,
        cartCount,
        cartFeedback,
        triggerFeedback
      }}
    >
      {children}
    </CartContext.Provider>
  );
};

export const useCart = () => {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
};
