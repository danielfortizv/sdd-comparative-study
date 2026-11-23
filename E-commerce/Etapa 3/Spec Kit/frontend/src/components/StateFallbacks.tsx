import React from "react";

export const LoadingFallback: React.FC = () => {
  return (
    <div
      data-testid="loading-state"
      style={{
        padding: "40px",
        textAlign: "center",
        color: "#666",
        fontSize: "16px",
      }}
    >
      <p>Loading products, please wait...</p>
    </div>
  );
};

export const EmptyCatalogFallback: React.FC = () => {
  return (
    <div
      data-testid="empty-catalog-state"
      style={{
        padding: "40px",
        textAlign: "center",
        color: "#666",
        fontSize: "16px",
      }}
    >
      <p>No products are currently available in the catalog offering.</p>
    </div>
  );
};

export interface ErrorFallbackProps {
  message: string;
  onRetry?: () => void;
}

export const ErrorFallback: React.FC<ErrorFallbackProps> = ({ message, onRetry }) => {
  return (
    <div
      data-testid="error-state"
      style={{
        padding: "30px",
        backgroundColor: "#fde8e8",
        border: "1px solid #f8b4b4",
        borderRadius: "4px",
        color: "#9b1c1c",
        margin: "20px 0",
        textAlign: "center",
      }}
    >
      <h3 style={{ marginTop: 0, fontSize: "16px", fontWeight: "bold" }}>An Error Occurred</h3>
      <p style={{ margin: "10px 0", fontSize: "14px" }}>{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          style={{
            padding: "8px 16px",
            backgroundColor: "#c81e1e",
            color: "#fff",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
            fontSize: "14px",
            fontWeight: 500,
          }}
        >
          Retry Action
        </button>
      )}
    </div>
  );
};
