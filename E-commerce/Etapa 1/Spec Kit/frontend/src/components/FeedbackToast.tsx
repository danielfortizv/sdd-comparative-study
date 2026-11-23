import React, { createContext, useContext, useState, ReactNode } from "react";

export interface ToastMessage {
  id: string;
  text: string;
  type: "success" | "error" | "info";
}

export interface ToastContextType {
  showToast: (text: string, type?: "success" | "error" | "info") => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const showToast = (text: string, type: "success" | "error" | "info" = "info") => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, text, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div
        className="toast-container"
        style={{
          position: "fixed",
          bottom: "20px",
          right: "20px",
          zIndex: 9999,
          display: "flex",
          flexDirection: "column",
          gap: "10px",
        }}
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            data-testid="feedback-toast"
            className={`toast toast-${toast.type}`}
            style={{
              padding: "12px 20px",
              borderRadius: "4px",
              color: "#fff",
              backgroundColor:
                toast.type === "success"
                  ? "#2e7d32"
                  : toast.type === "error"
                  ? "#d32f2f"
                  : "#0288d1",
              boxShadow: "0 2px 5px rgba(0,0,0,0.2)",
              fontSize: "14px",
              fontWeight: 500,
              minWidth: "200px",
              transition: "all 0.3s ease",
            }}
          >
            {toast.text}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
};
