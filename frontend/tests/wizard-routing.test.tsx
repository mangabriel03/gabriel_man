import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { AppRoutes } from "../src/AppRoutes";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  );
}

describe("wizard routing", () => {
  it("redirects `/` to the itinerary step", () => {
    renderAt("/");
    expect(
      screen.getByRole("heading", { name: /primary flight itinerary/i }),
    ).toBeInTheDocument();
  });

  it("Back is disabled on step 1", () => {
    renderAt("/case/new/itinerary");
    expect(screen.getByRole("button", { name: /^back$/i })).toBeDisabled();
  });

  it("blocks Next when required fields are empty", async () => {
    const user = userEvent.setup();
    renderAt("/case/new/itinerary");
    await user.click(screen.getByRole("button", { name: /^next$/i }));
    // Still on itinerary — heading unchanged
    expect(
      screen.getByRole("heading", { name: /primary flight itinerary/i }),
    ).toBeInTheDocument();
  });

  it("unknown route falls back to itinerary", () => {
    renderAt("/some/nonsense/path");
    expect(
      screen.getByRole("heading", { name: /primary flight itinerary/i }),
    ).toBeInTheDocument();
  });
});
