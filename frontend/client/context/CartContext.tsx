"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";

export interface CartItem {
  id: number;
  name: string;
  price: number;
  quantity: number;
  image?: string | null;
  stock?: number;
  variantId?: number;
  variantName?: string;
  wristSize?: string;
  lineKey?: string;
}

interface CartContextType {
  cartItems: CartItem[];
  addToCart: (product: Partial<CartItem>, quantity?: number) => void;
  removeFromCart: (product: Partial<CartItem>) => void;
  increaseQuantity: (product: Partial<CartItem>) => void;
  decreaseQuantity: (product: Partial<CartItem>) => void;
  clearCart: () => void;
  shippingMode: "post" | "pickup";
  setShippingMode: (mode: "post" | "pickup") => void;
}

const CartContext = createContext<CartContextType | undefined>(undefined);

function buildLineKey(item: Partial<CartItem>): string {
  if (!item) return "";
  if (item.variantId) return `variant-${item.variantId}`;
  if (item.id) return `product-${item.id}`;
  return `name-${item.name || Math.random()}`;
}

function normalizeItem(item: Partial<CartItem>): CartItem | null {
  if (!item || !item.id) return null;
  return {
    id: item.id,
    name: item.name || "",
    price: item.price || 0,
    quantity: item.quantity || 1,
    image: item.image,
    stock: item.stock,
    variantId: item.variantId,
    variantName: item.variantName,
    wristSize: item.wristSize,
    lineKey: item.lineKey || buildLineKey(item),
  };
}

export function CartProvider({ children }: { children: ReactNode }) {
  const [cartItems, setCartItems] = useState<CartItem[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const stored = localStorage.getItem("cartItems");
      const parsed = stored ? JSON.parse(stored) : [];
      return Array.isArray(parsed)
        ? parsed.map(normalizeItem).filter((x): x is CartItem => x !== null)
        : [];
    } catch {
      return [];
    }
  });

  const [shippingMode, setShippingMode] = useState<"post" | "pickup">(() => {
    if (typeof window === "undefined") return "post";
    try {
      const stored = localStorage.getItem("shippingMode");
      return (stored === "pickup" ? "pickup" : "post") as "post" | "pickup";
    } catch {
      return "post";
    }
  });

  useEffect(() => {
    localStorage.setItem("cartItems", JSON.stringify(cartItems));
  }, [cartItems]);

  useEffect(() => {
    localStorage.setItem("shippingMode", shippingMode);
  }, [shippingMode]);

  const addToCart = (product: Partial<CartItem>, quantity = 1) => {
    const priceNum =
      typeof product.price === "number"
        ? product.price
        : parseFloat(String(product.price || 0).replace(",", "."));

    const itemToAdd = normalizeItem({ ...product, price: priceNum, quantity });
    if (!itemToAdd) return;

    setCartItems((prev) => {
      const existing = prev.find((item) => item.lineKey === itemToAdd.lineKey);
      if (existing) {
        const max =
          typeof existing.stock === "number" && Number.isFinite(existing.stock)
            ? existing.stock
            : undefined;
        const nextQty = existing.quantity + quantity;
        const cappedQty = typeof max === "number" ? Math.min(nextQty, max) : nextQty;
        return prev.map((item) =>
          item.lineKey === itemToAdd.lineKey ? { ...item, quantity: cappedQty } : item
        );
      } else {
        return [...prev, itemToAdd];
      }
    });
  };

  const removeFromCart = (product: Partial<CartItem>) => {
    const key = product?.lineKey || buildLineKey(product);
    setCartItems((prev) => prev.filter((item) => item.lineKey !== key));
  };

  const increaseQuantity = (product: Partial<CartItem>) => {
    const key = product?.lineKey || buildLineKey(product);
    setCartItems((prev) =>
      prev.map((item) => {
        if (item.lineKey !== key) return item;
        const max =
          typeof item.stock === "number" && Number.isFinite(item.stock)
            ? item.stock
            : undefined;
        const next = item.quantity + 1;
        return typeof max === "number"
          ? { ...item, quantity: Math.min(next, max) }
          : { ...item, quantity: next };
      })
    );
  };

  const decreaseQuantity = (product: Partial<CartItem>) => {
    const key = product?.lineKey || buildLineKey(product);
    setCartItems((prev) =>
      prev
        .map((item) =>
          item.lineKey === key ? { ...item, quantity: item.quantity - 1 } : item
        )
        .filter((item) => item.quantity > 0)
    );
  };

  const clearCart = () => {
    setCartItems([]);
    localStorage.removeItem("cartItems");
  };

  return (
    <CartContext.Provider
      value={{
        cartItems,
        addToCart,
        removeFromCart,
        increaseQuantity,
        decreaseQuantity,
        clearCart,
        shippingMode,
        setShippingMode,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart(): CartContextType {
  const context = useContext(CartContext);
  if (context === undefined) {
    throw new Error("useCart must be used within a CartProvider");
  }
  return context;
}
