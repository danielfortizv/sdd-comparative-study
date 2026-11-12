export interface Product {
  product_id: string;
  name: string;
  representative_image: string;
  short_description: string;
  price: number;
  general_availability: string;
}

export interface CheckoutItem {
  product_id: string;
  quantity: number;
}

export interface CheckoutResponse {
  message: string;
  purchase_summary: {
    items: {
      product_id: string;
      name: string;
      quantity: number;
      unit_price: number;
      subtotal: number;
    }[];
    accumulated_total: number;
  };
}

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

/**
 * Helper to handle standard response parsing and error handling.
 */
async function handleResponse<T>(response: Response): Promise<T> {
  const isJson = response.headers.get("content-type")?.includes("application/json");
  const data = isJson ? await response.json() : null;

  if (!response.ok) {
    const errorMsg = data?.error || data?.detail || `HTTP error! Status: ${response.status}`;
    throw new Error(errorMsg);
  }

  return data as T;
}

export const api = {
  /**
   * Retrieves products from the catalog.
   */
  async getProducts(): Promise<Product[]> {
    const response = await fetch(`${API_BASE_URL}/api/products`);
    return handleResponse<Product[]>(response);
  },

  /**
   * Registers a new user account.
   */
  async registerUser(identifier: string, password: string): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE_URL}/api/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ identifier, password }),
    });
    return handleResponse<{ message: string }>(response);
  },

  /**
   * Authentic credentials to activate an authenticated session.
   */
  async signInUser(identifier: string, password: string): Promise<{ session_token: string }> {
    const response = await fetch(`${API_BASE_URL}/api/signin`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ identifier, password }),
    });
    return handleResponse<{ session_token: string }>(response);
  },

  /**
   * Terminates active session on the backend.
   */
  async signOutUser(token: string): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE_URL}/api/signout`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
      },
    });
    return handleResponse<{ message: string }>(response);
  },

  /**
   * Submits the simulated checkout request.
   */
  async checkout(
    token: string,
    items: CheckoutItem[],
    demonstrationInfo: Record<string, string>
  ): Promise<CheckoutResponse> {
    const response = await fetch(`${API_BASE_URL}/api/checkout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
      },
      body: JSON.stringify({
        items,
        demonstration_info: demonstrationInfo,
      }),
    });
    return handleResponse<CheckoutResponse>(response);
  },
};
