import React from "react";
import Catalog from "../components/Catalog";
import Cart from "../components/Cart";

interface CatalogPageProps {
  onProceedToCheckout: () => void;
}

export const CatalogPage: React.FC<CatalogPageProps> = ({ onProceedToCheckout }) => {
  return (
    <div className="catalog-page" data-testid="catalog-page" style={{ display: "flex", flexDirection: "column", gap: "30px" }}>
      <Catalog />
      <Cart onProceedToCheckout={onProceedToCheckout} />
    </div>
  );
};
export default CatalogPage;
