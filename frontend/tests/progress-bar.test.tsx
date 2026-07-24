import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { AppRoutes } from "../src/AppRoutes";

describe("ProgressBar", () => {
  it("marks all future step chips as aria-disabled=true", () => {
    render(
      <MemoryRouter initialEntries={["/case/new/itinerary"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    const chipPassenger = screen.getByRole("button", { name: /passenger/i });
    expect(chipPassenger).toHaveAttribute("aria-disabled", "true");
    expect(chipPassenger).toHaveAttribute("tabindex", "-1");
  });

  it("current step chip has aria-current=step", () => {
    render(
      <MemoryRouter initialEntries={["/case/new/itinerary"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    const chipItinerary = screen.getByRole("button", { name: /^itinerary/i });
    expect(chipItinerary).toHaveAttribute("aria-current", "step");
  });

  it("clicking a future step chip does nothing (no navigation)", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/case/new/itinerary"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    await user.click(screen.getByRole("button", { name: /passenger/i }));
    // Still on itinerary
    expect(
      screen.getByRole("heading", { name: /primary flight itinerary/i }),
    ).toBeInTheDocument();
  });
});
