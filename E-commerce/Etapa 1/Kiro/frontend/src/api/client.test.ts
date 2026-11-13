// Unit tests for the HTTP/JSON API client (Requirements 14.3, 14.4, 12.1/12.2,
// 12.4). These mock global `fetch` to verify success parsing, structured-error
// capture, and transport-failure handling without a running backend.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { API_BASE_URL, ApiError, apiClient } from "./client";
import type {
  CheckoutConfirmation,
  Credentials,
  Product,
} from "../types";

/** Build a minimal `Response`-like object for the mocked fetch. */
function jsonResponse(
  body: unknown,
  init?: { ok?: boolean; status?: number; throwOnJson?: boolean },
): Response {
  const ok = init?.ok ?? true;
  const status = init?.status ?? (ok ? 200 : 400);
  return {
    ok,
    status,
    json: init?.throwOnJson
      ? () => Promise.reject(new SyntaxError("Unexpected end of JSON input"))
      : () => Promise.resolve(body),
  } as unknown as Response;
}

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

describe("apiClient success parsing", () => {
  it("GET /products returns the parsed product array", async () => {
    const products: Product[] = [
      {
        id: "p1",
        name: "Widget",
        imageUrl: "http://img/p1.png",
        description: "A widget",
        price: 9.99,
        available: true,
      },
    ];
    fetchMock.mockResolvedValueOnce(jsonResponse(products));

    const result = await apiClient.listProducts();

    expect(result).toEqual(products);
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE_URL}/products`,
      expect.objectContaining({
        headers: { "Content-Type": "application/json" },
      }),
    );
  });

  it("GET /products/{id} encodes the id in the path", async () => {
    const product: Product = {
      id: "a/b",
      name: "Gadget",
      imageUrl: "http://img/g.png",
      description: "A gadget",
      price: 1,
      available: false,
    };
    fetchMock.mockResolvedValueOnce(jsonResponse(product));

    const result = await apiClient.getProduct("a/b");

    expect(result).toEqual(product);
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE_URL}/products/a%2Fb`,
      expect.anything(),
    );
  });

  it("POST /auth/register returns the account identity on 201", async () => {
    const credentials: Credentials = { identifier: "alice", password: "pw" };
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ id: "acc-1", identifier: "alice" }, { status: 201 }),
    );

    const result = await apiClient.register(credentials);

    expect(result).toEqual({ id: "acc-1", identifier: "alice" });
    const [, init] = fetchMock.mock.calls[0];
    expect(init).toMatchObject({ method: "POST" });
    expect(JSON.parse(init.body)).toEqual(credentials);
  });

  it("POST /auth/login returns the session representation", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ active: true, customerId: "acc-1" }),
    );

    const result = await apiClient.login({
      identifier: "alice",
      password: "pw",
    });

    expect(result).toEqual({ active: true, customerId: "acc-1" });
  });

  it("POST /auth/logout returns an inactive session", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ active: false, customerId: null }),
    );

    const result = await apiClient.logout();

    expect(result).toEqual({ active: false, customerId: null });
    const [, init] = fetchMock.mock.calls[0];
    expect(init).toMatchObject({ method: "POST" });
  });

  it("POST /checkout/confirm returns the confirmation summary", async () => {
    const confirmation: CheckoutConfirmation = {
      items: [
        {
          productId: "p1",
          name: "Widget",
          unitPrice: 9.99,
          quantity: 2,
          lineTotal: 19.98,
        },
      ],
      total: 19.98,
      simulated: true,
    };
    fetchMock.mockResolvedValueOnce(jsonResponse(confirmation));

    const result = await apiClient.confirmCheckout({
      items: [{ productId: "p1", quantity: 2 }],
    });

    expect(result).toEqual(confirmation);
  });
});

describe("apiClient error handling", () => {
  it("throws ApiError with status on a non-OK response", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({}, { ok: false, status: 500 }));

    const error = await apiClient.listProducts().catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(500);
  });

  it("captures the 404 product structured detail", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        {
          error: "not_found",
          message: "Unknown product",
          productId: "p9",
        },
        { ok: false, status: 404 },
      ),
    );

    const error = (await apiClient
      .getProduct("p9")
      .catch((e) => e)) as ApiError;

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(404);
    expect(error.message).toBe("Unknown product");
    expect(error.detail).toMatchObject({
      error: "not_found",
      productId: "p9",
    });
  });

  it("captures the 422 registration field lists", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        {
          error: "invalid_registration",
          message: "Registration data is invalid.",
          emptyFields: ["identifier"],
          nonConformingFields: ["password"],
        },
        { ok: false, status: 422 },
      ),
    );

    const error = (await apiClient
      .register({ identifier: "", password: "x" })
      .catch((e) => e)) as ApiError;

    expect(error.status).toBe(422);
    expect(error.detail?.emptyFields).toEqual(["identifier"]);
    expect(error.detail?.nonConformingFields).toEqual(["password"]);
  });

  it("captures a 401 login error with only an `error` field", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ error: "invalid_credentials" }, { ok: false, status: 401 }),
    );

    const error = (await apiClient
      .login({ identifier: "alice", password: "bad" })
      .catch((e) => e)) as ApiError;

    expect(error.status).toBe(401);
    // With no `message`, the error text falls back to the `error` field.
    expect(error.message).toBe("invalid_credentials");
    expect(error.detail).toMatchObject({ error: "invalid_credentials" });
  });

  it("flattens the nested `detail` of a 400 checkout error", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        { detail: { code: "empty_cart", message: "The cart is empty." } },
        { ok: false, status: 400 },
      ),
    );

    const error = (await apiClient
      .confirmCheckout({ items: [] })
      .catch((e) => e)) as ApiError;

    expect(error.status).toBe(400);
    expect(error.message).toBe("The cart is empty.");
    expect(error.detail).toMatchObject({
      code: "empty_cart",
      message: "The cart is empty.",
    });
  });

  it("degrades to a status-only ApiError when the error body is not JSON", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(null, { ok: false, status: 502, throwOnJson: true }),
    );

    const error = (await apiClient.listProducts().catch((e) => e)) as ApiError;

    expect(error.status).toBe(502);
    expect(error.detail).toBeNull();
    expect(error.message).toContain("/products");
  });

  it("throws a transport ApiError (status 0) when fetch rejects", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    const error = (await apiClient.listProducts().catch((e) => e)) as ApiError;

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(0);
    expect(error.detail).toBeNull();
  });
});
