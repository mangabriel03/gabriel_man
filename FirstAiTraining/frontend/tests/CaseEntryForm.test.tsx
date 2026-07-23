import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CaseEntryForm } from "../src/features/case-entry/CaseEntryForm";


const fetchMock = vi.fn();
beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});


function makeSmallFile(name: string, mime: string): File {
  return new File([new Uint8Array([0, 1, 2, 3])], name, { type: mime });
}


describe("CaseEntryForm", () => {
  it("renders all five sections", () => {
    render(<CaseEntryForm />);
    expect(screen.getByRole("heading", { name: /primary flight itinerary/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /connecting flights/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /passenger details/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /documents/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /gdpr/i })).toBeInTheDocument();
  });

  it("keeps submit disabled until form is valid", () => {
    render(<CaseEntryForm />);
    expect(screen.getByRole("button", { name: /submit claim/i })).toBeDisabled();
  });

  it("maps server 400 field errors into inline messages", async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (String(url).includes("/api/airports/")) {
        return {
          ok: true,
          json: async () => [
            { iata: "OTP", icao: "LROP", name: "Henri Coanda",
              city: "Bucharest", country: "Romania" },
            { iata: "CDG", icao: "LFPG", name: "Charles de Gaulle",
              city: "Paris", country: "France" },
          ],
        };
      }
      // POST /api/cases/ → 400
      return {
        ok: false,
        status: 400,
        json: async () => ({
          payload: { passenger: { email: ["Enter a valid email address."] } },
        }),
      };
    });

    render(<CaseEntryForm />);
    // Fill in valid-looking values so the client-side Zod resolver accepts submit.
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/first name/i), "Ana");
    await user.type(screen.getByLabelText(/last name/i), "Popescu");
    await user.type(screen.getByLabelText(/date of birth/i), "1990-05-14");
    await user.type(screen.getByLabelText(/^email/i), "invalid-but-passes-client@example.com");
    await user.type(screen.getByLabelText(/phone/i), "+40 712 345 678");
    await user.type(screen.getByLabelText(/address/i), "Str. Exemplu 1");
    await user.type(screen.getByLabelText(/postal code/i), "010101");
    await user.type(screen.getByLabelText(/reservation number/i), "ABC123");
    await user.type(screen.getByLabelText(/^flight date/i), "2026-08-01");
    await user.type(screen.getByLabelText(/^flight number/i), "AF1234");
    await user.type(screen.getByLabelText(/^airline/i), "Air France");
    // Depart / arrive airports via autocomplete
    const dep = screen.getByLabelText(/departing airport/i);
    await user.type(dep, "OT");
    await user.click(await screen.findByRole("option", { name: /OTP/i }));
    const arr = screen.getByLabelText(/destination airport/i);
    await user.type(arr, "CD");
    await user.click(await screen.findByRole("option", { name: /CDG/i }));
    await user.type(screen.getByLabelText(/planned departure time/i), "2026-08-01T09:00");
    await user.type(screen.getByLabelText(/planned arrival time/i), "2026-08-01T11:30");
    await user.upload(
      screen.getByLabelText(/boarding pass/i),
      makeSmallFile("bp.pdf", "application/pdf"),
    );
    await user.upload(
      screen.getByLabelText(/id or passport/i),
      makeSmallFile("id.pdf", "application/pdf"),
    );
    await user.click(screen.getByLabelText(/i agree to the gdpr/i));

    await user.click(screen.getByRole("button", { name: /submit claim/i }));

    await waitFor(() =>
      expect(screen.getByText(/enter a valid email address/i)).toBeInTheDocument(),
    );
  });
});
