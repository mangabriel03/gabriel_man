import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { AppRoutes } from "../src/AppRoutes";


describe("admin home", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("renders the admin action cards from backend navigation metadata", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify({
      actions: [
        {
          key: "new-user",
          label: "New User View",
          href: "/admin/users#create-user",
          description: "Create colleague accounts with a temporary password.",
        },
        {
          key: "user-view",
          label: "User View",
          href: "/admin/users",
          description: "Review all accounts, roles, and assigned case volume.",
        },
        {
          key: "case-view",
          label: "Case View",
          href: "/admin/cases",
          description: "Open the full case directory and manage stored records.",
        },
        {
          key: "system-view",
          label: "System View",
          href: "/admin/system",
          description: "Open system options and configuration placeholders.",
        },
      ],
    }), { status: 200, headers: { "Content-Type": "application/json" } }));

    render(
      <MemoryRouter initialEntries={["/admin"]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: /admin view/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^New User View$/i })).toHaveAttribute("href", "/admin/users#create-user");
    expect(screen.getByRole("link", { name: /^User View$/i })).toHaveAttribute("href", "/admin/users");
    expect(screen.getByRole("link", { name: /^Case View$/i })).toHaveAttribute("href", "/admin/cases");
    expect(screen.getByRole("link", { name: /^System View$/i })).toHaveAttribute("href", "/admin/system");
  });

  it("keeps the system view reachable from the landing page", async () => {
    const user = userEvent.setup();
    vi.mocked(fetch)
      .mockResolvedValueOnce(new Response(JSON.stringify({
        actions: [
          {
            key: "system-view",
            label: "System View",
            href: "/admin/system",
            description: "Open system options and configuration placeholders.",
          },
        ],
      }), { status: 200, headers: { "Content-Type": "application/json" } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        actions: [
          {
            key: "system-view",
            label: "System View",
            href: "/admin/system",
            description: "Open system options and configuration placeholders.",
          },
        ],
      }), { status: 200, headers: { "Content-Type": "application/json" } }));

    render(
      <MemoryRouter initialEntries={["/admin"]}>
        <AppRoutes />
      </MemoryRouter>,
    );

    await user.click(await screen.findByRole("link", { name: /^System View$/i }));

    expect(await screen.findByRole("heading", { name: /system view/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /back to admin view/i })).toHaveAttribute("href", "/admin");
  });
});