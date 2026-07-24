import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { AppRoutes } from "../src/AppRoutes";


describe("admin user list", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("renders users, roles, case counts, and actions", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify([
      {
        id: 1,
        name: "Ada Admin",
        email: "admin@example.com",
        role: "SYSTEM_ADMIN",
        assigned_case_count: 0,
      },
      {
        id: 2,
        name: "Pia Passenger",
        email: "pia@example.com",
        role: "PASSENGER",
        assigned_case_count: 2,
      },
    ]), { status: 200, headers: { "Content-Type": "application/json" } }));

    render(
      <MemoryRouter initialEntries={["/admin/users"]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("columnheader", { name: /assigned cases/i })).toBeInTheDocument();
    expect(screen.getByText("Ada Admin")).toBeInTheDocument();
    expect(screen.getByText("Pia Passenger")).toBeInTheDocument();
    expect(screen.getByText("System Admin")).toBeInTheDocument();
    expect(screen.getByText("Passenger")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "2" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /edit|delete/i })).toHaveLength(4);
  });

  it("creates a colleague account and shows a confirmation banner", async () => {
    const user = userEvent.setup();
    vi.mocked(fetch)
      .mockResolvedValueOnce(new Response(JSON.stringify([
        {
          id: 1,
          name: "Ada Admin",
          email: "admin@example.com",
          role: "SYSTEM_ADMIN",
          assigned_case_count: 0,
        },
      ]), { status: 200, headers: { "Content-Type": "application/json" } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        id: 2,
        name: "Cole League",
        email: "colleague@example.com",
        role: "COLLEAGUE",
        assigned_case_count: 0,
        detail: "Account created for colleague@example.com. The temporary password was emailed to the colleague.",
      }), { status: 201, headers: { "Content-Type": "application/json" } }));

    render(
      <MemoryRouter initialEntries={["/admin/users"]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: /user directory/i })).toBeInTheDocument();

    await user.type(screen.getByLabelText(/first name/i), "Cole");
    await user.type(screen.getByLabelText(/last name/i), "League");
    await user.type(screen.getByLabelText(/e-mail address/i), "colleague@example.com");
    await user.type(screen.getByLabelText(/initial password/i), "ColleaguePass123!");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByText(/account created for colleague@example.com/i)).toBeInTheDocument();
    expect(screen.getByText("Cole League")).toBeInTheDocument();
    expect(vi.mocked(fetch)).toHaveBeenNthCalledWith(
      2,
      "/api/admin/users/",
      expect.objectContaining({
        method: "POST",
      }),
    );
  });
});