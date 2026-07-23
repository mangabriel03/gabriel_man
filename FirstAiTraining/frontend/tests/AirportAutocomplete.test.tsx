import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AirportAutocomplete } from "../src/features/case-entry/AirportAutocomplete";

const fetchMock = vi.fn();
beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

describe("AirportAutocomplete", () => {
  it("queries the API after debounce and calls onChange on selection", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => [
        { iata: "CDG", icao: "LFPG", name: "Charles de Gaulle",
          city: "Paris", country: "France" },
      ],
    });

    const onChange = vi.fn();
    render(
      <AirportAutocomplete id="dep" label="From" value="" onChange={onChange} />,
    );

    const input = screen.getByLabelText("From");
    await userEvent.type(input, "CDG");

    const option = await waitFor(() => screen.getByRole("option"));
    expect(option).toHaveTextContent("Charles de Gaulle");

    await userEvent.click(option);
    expect(onChange).toHaveBeenCalledWith("CDG");
  });
});
