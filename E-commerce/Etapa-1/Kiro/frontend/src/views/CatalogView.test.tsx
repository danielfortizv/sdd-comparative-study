// Unit tests for the Catalog view (task 8.1).
//
// These mock the API client (vi.mock) so the component can be rendered without
// a running backend, and wrap renders in the real JourneyProvider so the view
// consumes the shared journey state exactly as it does in the app.
//
// Covered behavior:
// - products render with all commercial fields (name, image, description,
//   price, availability) — R1.3
// - images carry accessible alt text equal to the product name — R13.2/R13.3
// - the add action calls addToCart on the shared state — R2.1
// - the expanded product view shows the same commercial fields — R1.4/R1.5

import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CatalogView } from "./CatalogView";
import { JourneyProvider, useJourney } from "../state/JourneyState";
import type { Product } from "../types";

// Mock the API client module so no real network request is made.
vi.mock("../api/client", () => ({
  apiClient: {
    listProducts: vi.fn(),
    getProduct: vi.fn(),
  },
}));

// Import the mocked client after vi.mock so the typed mock is available.
import { apiClient } from "../api/client";

const listProductsMock = vi.mocked(apiClient.listProducts);

const PRODUCTS: Product[] = [
  {
    id: "p1",
    name: "Ceramic Mug",
    imageUrl: "http://img/mug.png",
    description: "A sturdy ceramic mug.",
    price: 12.5,
    available: true,
  },
  {
    id: "p2",
    name: "Steel Bottle",
    imageUrl: "http://img/bottle.png",
    description: "Keeps drinks cold.",
    price: 24,
    available: false,
  },
];

/** A probe that exposes the shared cart so tests can assert add actions. */
function CartProbe() {
  const { cart } = useJourney();
  return (
    <div data-testid="cart-probe">
      {cart.map((item) => `${item.productId}:${item.quantity}`).join(",")}
    </div>
  );
}

function renderCatalog() {
  return render(
    <JourneyProvider>
      <CatalogView />
      <CartProbe />
    </JourneyProvider>,
  );
}

beforeEach(() => {
  listProductsMock.mockReset();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("CatalogView", () => {
  it("shows a loading indicator while the catalog request is in flight", async () => {
    // A pending promise keeps the view in its loading state.
    listProductsMock.mockReturnValue(new Promise<Product[]>(() => {}));

    renderCatalog();

    expect(screen.getByText(/loading catalog/i)).toBeInTheDocument();
  });

  it("renders each product with all commercial fields", async () => {
    listProductsMock.mockResolvedValue(PRODUCTS);

    renderCatalog();

    // Wait for the first product to appear once loading resolves.
    expect(
      await screen.findByRole("heading", { name: "Ceramic Mug" }),
    ).toBeInTheDocument();

    // Name, description, price, availability for product 1.
    expect(screen.getByText("A sturdy ceramic mug.")).toBeInTheDocument();
    expect(screen.getByText("$12.50")).toBeInTheDocument();
    expect(screen.getByText("Available")).toBeInTheDocument();

    // Product 2 and its "Unavailable" indication.
    expect(
      screen.getByRole("heading", { name: "Steel Bottle" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Keeps drinks cold.")).toBeInTheDocument();
    expect(screen.getByText("$24.00")).toBeInTheDocument();
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
  });

  it("gives each product image accessible alt text equal to its name", async () => {
    listProductsMock.mockResolvedValue(PRODUCTS);

    renderCatalog();

    await screen.findByRole("heading", { name: "Ceramic Mug" });

    expect(screen.getByRole("img", { name: "Ceramic Mug" })).toHaveAttribute(
      "src",
      "http://img/mug.png",
    );
    expect(screen.getByRole("img", { name: "Steel Bottle" })).toHaveAttribute(
      "src",
      "http://img/bottle.png",
    );
  });

  it("adds a product to the shared cart when the add action is used", async () => {
    listProductsMock.mockResolvedValue(PRODUCTS);

    renderCatalog();

    const mugCard = (
      await screen.findByRole("heading", { name: "Ceramic Mug" })
    ).closest("li") as HTMLElement;

    fireEvent.click(
      within(mugCard).getByRole("button", { name: /add to cart/i }),
    );

    await waitFor(() => {
      expect(screen.getByTestId("cart-probe")).toHaveTextContent("p1:1");
    });
  });

  it("shows the same commercial fields in the expanded product view", async () => {
    listProductsMock.mockResolvedValue(PRODUCTS);

    renderCatalog();

    const mugCard = (
      await screen.findByRole("heading", { name: "Ceramic Mug" })
    ).closest("li") as HTMLElement;

    fireEvent.click(
      within(mugCard).getByRole("button", { name: /view details/i }),
    );

    // The expanded panel repeats the same commercial fields as the list entry.
    const detailsId = within(mugCard)
      .getByRole("button", { name: /hide details/i })
      .getAttribute("aria-controls") as string;
    const panel = document.getElementById(detailsId) as HTMLElement;

    expect(
      within(panel).getByRole("heading", { name: "Ceramic Mug" }),
    ).toBeInTheDocument();
    expect(
      within(panel).getByRole("img", { name: "Ceramic Mug" }),
    ).toHaveAttribute("src", "http://img/mug.png");
    expect(
      within(panel).getByText("A sturdy ceramic mug."),
    ).toBeInTheDocument();
    expect(within(panel).getByText("$12.50")).toBeInTheDocument();
    expect(within(panel).getByText("Available")).toBeInTheDocument();
  });

  it("shows a request-failure message when the catalog cannot be loaded", async () => {
    listProductsMock.mockRejectedValue(new Error("network down"));

    renderCatalog();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /catalog could not be loaded/i,
    );
  });

  it("shows an empty-state indication when no products are returned", async () => {
    listProductsMock.mockResolvedValue([]);

    renderCatalog();

    expect(
      await screen.findByText(/no products are available/i),
    ).toBeInTheDocument();
  });
});
