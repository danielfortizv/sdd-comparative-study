import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { Product } from "../services/api";

export interface CartItem {
  product_id: string;
  name: string;
  unit_price: number;
  quantity: number;
  subtotal: number;
}

export interface CartContextType {
  items: CartItem[];
  accumulated_total: number;
  addItem: (product: Product) => void;
  updateQuantity: (productId: string, quantity: number) => void;
  removeItem: (productId: string) => void;
  clearCart: () => void;
}

const CartContext = createContext<CartContextType | undefined>(undefined);

export const CartProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [items, setItems] = useState<CartItem[]>([]);
  const [accumulated_total, setAccumulatedTotal] = useState<number>(0);

  // Recalculate accumulated total whenever items change
  useEffect(() => {
    const total = items.reduce((sum, item) => sum + item.subtotal, 0);
    setAccumulatedTotal(Number(total.toFixed(2)));
  }, [items]);

  const addItem = (product: Product) => {
    setItems((prevItems) => {
      const existingIndex = prevItems.findIndex((item) => item.product_id === product.product_id);
      if (existingIndex > -1) {
        // Increment quantity of existing item
        const updated = [...prevItems];
        const item = updated[existingIndex];
        const newQty = item.quantity + 1;
        updated[existingIndex] = {
          ...item,
          quantity: newQty,
          subtotal: Number((item.unit_price * newQty).toFixed(2)),
        };
        return updated;
      } else {
        // Add new item to cart
        return [
          ...prevItems,
          {
            product_id: product.product_id,
            name: product.name,
            unit_price: product.price,
            quantity: 1,
            subtotal: product.price,
          },
        ];
      }
    });
  };

  const updateQuantity = (productId: string, quantity: number) => {
    if (quantity <= 0) {
      removeItem(productId);
      return;
    }
    setItems((prevItems) =>
      prevItems.map((item) =>
        item.product_id === productId
          ? {
              ...item,
              quantity,
              subtotal: Number((item.unit_price * quantity).toFixed(2)),
            }
          : item
      )
    );
  };

  const removeItem = (productId: string) => {
    setItems((prevItems) => prevItems.filter((item) => item.product_id !== productId));
  };

  const clearCart = () => {
    setItems([]);
  };

  return (
    <CartContext.Provider
      value={{
        items,
        accumulated_total,
        addItem,
        updateQuantity,
        removeItem,
        clearCart,
      }}
    >
      {children}
    </CartContext.Provider>
  );
};

export const useCart = (): CartContextType => {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error("useCart must be used within a CartProvider");
  }
  return context;
};
