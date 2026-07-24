import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { AppRoutes } from "../src/AppRoutes";
import { SESSION_KEY } from "../src/features/case-entry/wizard/persistence";

describe("wizard sessionStorage persistence", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
    sessionStorage.clear();
  });

  it("persists form values under the shared key after debounce", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(
      <MemoryRouter initialEntries={["/case/new/passenger"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    await user.type(screen.getByLabelText(/first name/i), "Alice");
    vi.advanceTimersByTime(500);
    const raw = sessionStorage.getItem(SESSION_KEY);
    expect(raw).not.toBeNull();
    expect(JSON.parse(raw!).passenger.first_name).toBe("Alice");
  });

  it("hydrates from sessionStorage on mount, excluding files", () => {
    sessionStorage.setItem(
      SESSION_KEY,
      JSON.stringify({
        passenger: {
          first_name: "Bob",
          last_name: "",
          date_of_birth: "",
          email: "",
          phone: "",
          address: "",
          postal_code: "",
        },
        reservation_number: "",
        segments: [
          {
            order: 0,
            flight_date: "",
            flight_number: "",
            airline: "",
            departure_airport_iata: "",
            arrival_airport_iata: "",
            planned_departure_time: "",
            planned_arrival_time: "",
            is_problem_flight: true,
          },
        ],
        disruption: {
          disruption_type: "",
          cancellation_notice: null,
          delay_duration: null,
          denied_boarding_voluntary: null,
          denied_boarding_reason: null,
          airline_motive_mentioned: null,
          airline_motive: null,
          incident_description: "",
        },
        gdpr_consent: false,
      }),
    );
    render(
      <MemoryRouter initialEntries={["/case/new/passenger"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(screen.getByLabelText(/first name/i)).toHaveValue("Bob");
  });
});
