// Preview mini-grid rendering tests.

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Preview } from "./Preview";
import type { PieceType } from "./types";

describe("Preview", () => {
  it("renders an empty slot label when piece is null", () => {
    render(<Preview piece={null} label="Hold piece" />);
    expect(screen.getByTestId("preview-hold-piece")).toHaveAttribute(
      "aria-label",
      "Hold piece: empty",
    );
  });

  it.each(["I", "O", "T", "S", "Z", "J", "L"] as PieceType[])(
    "renders the %s piece type",
    (piece) => {
      render(<Preview piece={piece} label="Next piece" />);
      expect(screen.getByTestId("preview-next-piece")).toHaveAttribute(
        "aria-label",
        `Next piece: ${piece}`,
      );
    },
  );
});
