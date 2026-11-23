import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiClient } from "@kiro/api/client";

afterEach(() => vi.unstubAllGlobals());

describe("independent HTTP/JSON boundary", () => {
  it("loads products and sends the approved endpoint payloads", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([{ id: "p-001" }]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ active: true, customerId: "c-1" }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ active: false, customerId: null }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [], total: 0, simulated: true }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiClient.listProducts()).resolves.toEqual([{ id: "p-001" }]);
    await expect(apiClient.login({ identifier: "buyer", password: "secret" })).resolves.toMatchObject({ active: true });
    await expect(apiClient.logout()).resolves.toMatchObject({ active: false });
    await expect(apiClient.confirmCheckout({ items: [] })).resolves.toMatchObject({ simulated: true });
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });

  it("normalizes structured and transport failures without leaking internals", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: { code: "empty_cart", message: "Cannot proceed." } }), { status: 400 }),
    ));
    await expect(apiClient.confirmCheckout({ items: [] })).rejects.toMatchObject({
      name: "ApiError", status: 400, message: "Cannot proceed."
    });

    vi.stubGlobal("fetch", vi.fn().mockRejectedValueOnce(new Error("private transport detail")));
    try {
      await apiClient.listProducts();
      throw new Error("Expected ApiError");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect(String(error)).not.toContain("private transport detail");
    }
  });
});
