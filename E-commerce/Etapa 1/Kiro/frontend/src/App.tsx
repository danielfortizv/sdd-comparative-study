// Application shell wiring the view layer with the shared in-memory journey
// state. This wires the integrated journey (catalog -> cart -> authentication
// -> checkout) end to end (task 14.3).
//
// The four views all consume the single shared journey state (useJourney), so
// actions performed in any component are reflected in the others and product
// identity, quantities, and totals stay consistent across views
// (R11.1-R11.6). The checkout completion path resets to a comprehensible
// new-purchase state via clearCart.
//
// The shell presents the four components as one integrated system (R11.1):
// an accessible in-page navigation lets a person move between Catalog, Cart,
// Account, and Checkout, and each view is wrapped in an anchor target. The
// Account section carries id="account" so the Checkout identification gate's
// "#account" sign-in/register links resolve, keeping the journey continuous.

import { JourneyProvider } from "./state/JourneyState";
import { AuthView } from "./views/AuthView";
import { CartView } from "./views/CartView";
import { CatalogView } from "./views/CatalogView";
import { CheckoutView } from "./views/CheckoutView";

/** In-page navigation targets for the integrated journey. */
const JOURNEY_SECTIONS = [
  { id: "catalog", label: "Catalog" },
  { id: "cart", label: "Cart" },
  { id: "account", label: "Account" },
  { id: "checkout", label: "Checkout" },
] as const;

export function App() {
  return (
    <JourneyProvider>
      <header>
        <h1>E-Commerce Stage 1</h1>
        {/* Integrated-journey navigation: the four components are presented as
            one system a person can move through continuously (R11.1). Links
            resolve to the in-page anchor targets below. */}
        <nav aria-label="Journey navigation" className="journey-nav">
          <ul>
            {JOURNEY_SECTIONS.map((sectionLink) => (
              <li key={sectionLink.id}>
                <a href={`#${sectionLink.id}`}>{sectionLink.label}</a>
              </li>
            ))}
          </ul>
        </nav>
      </header>
      <main>
        {/* Each view shares the journey state, so changes propagate across the
            integrated system (R11.2-R11.6). Anchor targets keep the journey
            continuous; the Account target backs the Checkout gate's
            "#account" links (R8.1, R8.2). */}
        <div id="catalog">
          <CatalogView />
        </div>
        <div id="cart">
          <CartView />
        </div>
        <div id="account">
          <AuthView />
        </div>
        <div id="checkout">
          <CheckoutView />
        </div>
      </main>
    </JourneyProvider>
  );
}
