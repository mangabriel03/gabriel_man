import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { AppRoutes } from "../src/AppRoutes";
import * as casesApi from "../src/api/cases";

vi.mock("../src/api/cases", () => ({
  createCase: vi.fn(),
}));

const FULL_DRAFT = {
  passenger: {
    first_name: "Alice",
    last_name: "Smith",
    date_of_birth: "1990-01-01",
    email: "a@b.com",
    phone: "+123456789",
    address: "1 Rue",
    postal_code: "75001",
  },
  reservation_number: "ABC123",
  segments: [
    {
      order: 0,
      flight_date: "2026-01-01",
      flight_number: "AF001",
      airline: "AF",
      departure_airport_iata: "CDG",
      arrival_airport_iata: "JFK",
      planned_departure_time: "2026-01-01T10:00",
      planned_arrival_time: "2026-01-01T13:00",
      is_problem_flight: true,
    },
  ],
  disruption: {
    disruption_type: "DELAY",
    cancellation_notice: null,
    delay_duration: "MORE_THAN_3H",
    denied_boarding_voluntary: null,
    denied_boarding_reason: null,
    airline_motive_mentioned: "NO",
    airline_motive: null,
    incident_description: "5-hour delay.",
  },
  gdpr_consent: true,
};

describe("Review step", () => {
  beforeEach(() => {
    sessionStorage.clear();
    (casesApi.createCase as unknown as ReturnType<typeof vi.fn>).mockReset();
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  it("Edit link navigates to the target step with returnTo=review; Next returns to Review", async () => {
    const user = userEvent.setup();
    sessionStorage.setItem("airassist:case:draft", JSON.stringify(FULL_DRAFT));

    render(
      <MemoryRouter initialEntries={["/case/new/review"]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("heading", { name: /review your claim/i }),
    ).toBeInTheDocument();

    // Click Edit next to Passenger (order: Flights, Disruption, Passenger, Documents, Consent)
    const edits = screen.getAllByRole("button", { name: /^edit$/i });
    await user.click(edits[2]);
    expect(
      screen.getByRole("heading", { name: /passenger details/i }),
    ).toBeInTheDocument();

    // Change name and press Next — should return to Review, not Documents
    const fname = screen.getByLabelText(/first name/i);
    await user.clear(fname);
    await user.type(fname, "Alicia");
    await user.click(screen.getByRole("button", { name: /^next$/i }));
    expect(
      await screen.findByRole("heading", { name: /review your claim/i }),
    ).toBeInTheDocument();
  });

  it("Submit calls createCase and navigates to the success page", async () => {
    const user = userEvent.setup();
    sessionStorage.setItem("airassist:case:draft", JSON.stringify(FULL_DRAFT));

    (casesApi.createCase as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: "abc-123",
      status: "NEW",
      created_at: "2026-07-24T00:00:00Z",
      account_email: "a@b.com",
      password_change_required: true,
      distance_km: 5837,
      compensation_amount_eur: 600,
      compensation_error: null,
      disruption: {
        disruption_type: "DELAY",
        cancellation_notice: null,
        delay_duration: "MORE_THAN_3H",
        denied_boarding_voluntary: null,
        denied_boarding_reason: null,
        airline_motive_mentioned: "NO",
        airline_motive: null,
        incident_description: "5-hour delay.",
      },
    });

    render(
      <MemoryRouter initialEntries={["/case/new/documents"]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    const pdf = new File(["hi"], "bp.pdf", { type: "application/pdf" });
    const id = new File(["hi"], "id.pdf", { type: "application/pdf" });
    await user.upload(screen.getByLabelText(/boarding pass/i), pdf);
    await user.upload(screen.getByLabelText(/id or passport/i), id);
    await user.click(screen.getByRole("button", { name: /^next$/i })); // → consent
    await user.click(screen.getByRole("button", { name: /^next$/i })); // → review
    expect(
      await screen.findByRole("heading", { name: /review your claim/i }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /submit claim/i }));

    expect(
      await screen.findByRole("heading", { name: /your claim was received/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/abc-123/)).toBeInTheDocument();
  });
});
