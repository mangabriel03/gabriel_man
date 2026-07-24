import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { AppRoutes } from "../src/AppRoutes";


describe("admin case list", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    vi.stubGlobal("confirm", vi.fn(() => true));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("renders cases with their reference fields and delete action", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify([
      {
        id: "95e04f69-2b59-4b22-89f5-8de72f7ff43a",
        case_date: "2026-07-24",
        flight_number: "AF1234",
        flight_date: "2026-07-30",
        status: "NEW",
      },
    ]), { status: 200, headers: { "Content-Type": "application/json" } }));

    render(
      <MemoryRouter initialEntries={["/admin/cases"]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("columnheader", { name: /flight number/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /95e04f69-2b59-4b22-89f5-8de72f7ff43a/i })).toHaveAttribute(
      "href",
      "/case/created/95e04f69-2b59-4b22-89f5-8de72f7ff43a",
    );
    expect(screen.getByText("AF1234")).toBeInTheDocument();
    expect(screen.getByText("2026-07-30")).toBeInTheDocument();
    expect(screen.getByText("NEW")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /delete/i })).toBeInTheDocument();
  });

  it("deletes a case and shows a confirmation banner", async () => {
    const user = userEvent.setup();
    vi.mocked(fetch)
      .mockResolvedValueOnce(new Response(JSON.stringify([
        {
          id: "95e04f69-2b59-4b22-89f5-8de72f7ff43a",
          case_date: "2026-07-24",
          flight_number: "AF1234",
          flight_date: "2026-07-30",
          status: "NEW",
        },
      ]), { status: 200, headers: { "Content-Type": "application/json" } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        detail: "Case 95e04f69-2b59-4b22-89f5-8de72f7ff43a deleted successfully.",
      }), { status: 200, headers: { "Content-Type": "application/json" } }));

    render(
      <MemoryRouter initialEntries={["/admin/cases"]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: /case directory/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /delete/i }));

    expect(await screen.findByText(/deleted successfully/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByText("AF1234")).not.toBeInTheDocument();
    });
    expect(vi.mocked(confirm)).toHaveBeenCalledOnce();
    expect(vi.mocked(fetch)).toHaveBeenNthCalledWith(
      2,
      "/api/admin/cases/95e04f69-2b59-4b22-89f5-8de72f7ff43a/",
      expect.objectContaining({
        method: "DELETE",
      }),
    );
  });
});