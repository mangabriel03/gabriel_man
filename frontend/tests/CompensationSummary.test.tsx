import { render, screen, waitFor, act } from "@testing-library/react";
import { useEffect } from "react";
import { FormProvider, useForm } from "react-hook-form";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CompensationSummary } from "../src/features/case-entry/CompensationSummary";
import type { CaseFormValues } from "../src/features/case-entry/schema";

const fetchMock = vi.fn();
beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

function Harness({ segments }: { segments: CaseFormValues["segments"] }) {
  const methods = useForm<CaseFormValues>({
    defaultValues: {
      passenger: {
        first_name: "",
        last_name: "",
        date_of_birth: "",
        email: "",
        phone: "",
        address: "",
        postal_code: "",
      },
      reservation_number: "",
      segments,
      gdpr_consent: false,
      boarding_pass: undefined as unknown as File,
      id_document: undefined as unknown as File,
    },
  });
  // RHF only reads defaultValues on mount; push prop updates through setValue
  // so that useWatch in the component observes the latest segments.
  useEffect(() => {
    methods.setValue("segments", segments);
  }, [segments, methods]);
  return (
    <FormProvider {...methods}>
      <CompensationSummary />
    </FormProvider>
  );
}

function seg(order: number, from: string, to: string) {
  return {
    order,
    flight_date: "",
    flight_number: "",
    airline: "",
    departure_airport_iata: from,
    arrival_airport_iata: to,
    planned_departure_time: "",
    planned_arrival_time: "",
    is_problem_flight: order === 0,
  };
}

describe("CompensationSummary", () => {
  it("renders nothing when no complete legs are present", () => {
    render(<Harness segments={[seg(0, "", "")]} />);
    expect(screen.queryByTestId("compensation-summary")).toBeNull();
  });

  it("shows the amount and distance on success", async () => {
    vi.useFakeTimers();
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        distance_km: "1874.00",
        compensation_amount_eur: 400,
        legs: [
          {
            from: "OTP",
            to: "CDG",
            distance_km: "1874.00",
            source: "airportgap",
            error: null,
          },
        ],
      }),
    });

    render(<Harness segments={[seg(0, "OTP", "CDG")]} />);
    await act(async () => {
      vi.advanceTimersByTime(500);
    });
    vi.useRealTimers();

    await waitFor(() =>
      expect(screen.getByText(/400\s*€/)).toBeInTheDocument(),
    );
    expect(screen.getByText(/1,?\s?874 km/)).toBeInTheDocument();
    expect(screen.getByText(/across 1 leg\(s\)\./)).toBeInTheDocument();
  });

  it("shows the soft-error copy on 422", async () => {
    vi.useFakeTimers();
    fetchMock.mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: "unavailable", legs: [] }),
    });

    render(<Harness segments={[seg(0, "OTP", "CDG")]} />);
    await act(async () => {
      vi.advanceTimersByTime(500);
    });
    vi.useRealTimers();

    await waitFor(() =>
      expect(
        screen.getByText(/couldn't calculate compensation/i),
      ).toBeInTheDocument(),
    );
  });

  it("debounces rapid segment changes into a single fetch", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        distance_km: "100.00",
        compensation_amount_eur: 250,
        legs: [
          {
            from: "OTP",
            to: "CDG",
            distance_km: "100.00",
            source: "airportgap",
            error: null,
          },
        ],
      }),
    });

    // Start empty (as the real form does), then apply three rapid changes
    // within the debounce window. Only the final one (LHR) should hit the API.
    const { rerender } = render(<Harness segments={[seg(0, "", "")]} />);
    rerender(<Harness segments={[seg(0, "OTP", "CDG")]} />);
    rerender(<Harness segments={[seg(0, "OTP", "AMS")]} />);
    rerender(<Harness segments={[seg(0, "OTP", "LHR")]} />);

    // Real timers: wait for the 400 ms debounce + microtasks.
    await waitFor(
      () => expect(fetchMock).toHaveBeenCalledTimes(1),
      { timeout: 2000 },
    );
    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(String(init.body))).toEqual({
      legs: [{ from: "OTP", to: "LHR" }],
    });
  });
});
