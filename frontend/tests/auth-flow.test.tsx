import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { AppRoutes } from "../src/AppRoutes";


describe("passenger auth flow", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("routes first-time login into mandatory password change and then back to login", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockResolvedValueOnce(new Response(JSON.stringify({
        email: "ana@example.com",
        first_name: "Ana",
        last_name: "Popescu",
        role: "PASSENGER",
        must_change_password: true,
      }), { status: 200, headers: { "Content-Type": "application/json" } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        must_change_password: false,
      }), { status: 200, headers: { "Content-Type": "application/json" } }));

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    await user.type(screen.getByLabelText(/email address/i), "ana@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "TempPass123!");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(
      await screen.findByRole("heading", { name: /change your temporary password/i }),
    ).toBeInTheDocument();

    await user.type(screen.getByLabelText(/^new password$/i), "EvenBetterPass123!");
    await user.type(screen.getByLabelText(/confirm new password/i), "EvenBetterPass123!");
    await user.click(screen.getByRole("button", { name: /update password/i }));

    expect(
      await screen.findByText(/password changed\. sign in again with your new password\./i),
    ).toBeInTheDocument();
    expect(screen.getByDisplayValue("ana@example.com")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/auth/change-password/",
      expect.objectContaining({
        method: "POST",
      }),
    );
  });

  it("routes system admins to the admin landing page after login", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockResolvedValueOnce(new Response(JSON.stringify({
        email: "admin@example.com",
        first_name: "Ada",
        last_name: "Admin",
        role: "SYSTEM_ADMIN",
        must_change_password: false,
      }), { status: 200, headers: { "Content-Type": "application/json" } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        actions: [
          {
            key: "case-view",
            label: "Case View",
            href: "/admin/cases",
            description: "Open the full case directory and manage stored records.",
          },
        ],
      }), { status: 200, headers: { "Content-Type": "application/json" } }));

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    await user.type(screen.getByLabelText(/email address/i), "admin@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "AdminPass123!");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("heading", { name: /admin view/i })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: /case view/i })).toHaveAttribute("href", "/admin/cases");
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/admin/navigation/", expect.any(Object));
  });

  it("shows account onboarding on the created-case page", async () => {
    render(
      <MemoryRouter
        initialEntries={[
          {
            pathname: "/case/created/abc-123",
            state: {
              id: "abc-123",
              status: "NEW",
              created_at: "2026-07-24T00:00:00Z",
              account_email: "ana@example.com",
              password_change_required: true,
              distance_km: 1200,
              compensation_amount_eur: 400,
              compensation_error: null,
              disruption: {
                disruption_type: "DELAY",
                cancellation_notice: null,
                delay_duration: "MORE_THAN_3H",
                denied_boarding_voluntary: null,
                denied_boarding_reason: null,
                airline_motive_mentioned: "NO",
                airline_motive: null,
                incident_description: "Delay.",
              },
            },
          },
        ]}
      >
        <AppRoutes />
      </MemoryRouter>,
    );

    expect(screen.getByText(/we emailed a temporary password to ana@example.com/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /go to passenger login/i })).toHaveAttribute("href", "/login");
  });
});