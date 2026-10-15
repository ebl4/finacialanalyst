import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("workspace connection", () => {
  it("offers organization-token login when demo mode is disabled", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: /clarity for the decisions that matter/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/secure access token/i)).toHaveAttribute("type", "password");
    expect(screen.queryByRole("button", { name: /guest analyst/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/reports analyzed/i)).not.toBeInTheDocument();
  });

  it("lets a guest analyst enter the workspace when demo mode is enabled", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      let body: unknown = {};
      if (url.endsWith("/auth/demo") && method === "GET") body = { enabled: true };
      else if (url.endsWith("/auth/demo") && method === "POST") {
        body = {
          access_token: "demo-token",
          display_name: "Guest Analyst",
          expires_in: 14400,
          role: "analyst",
          token_type: "Bearer",
        };
      } else if (url.endsWith("/reports") || url.endsWith("/approvals")) body = [];
      return {
        ok: true,
        status: 200,
        json: async () => body,
      } as Response;
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: /guest analyst/i }));

    await waitFor(() => {
      expect(screen.getByText("Guest Analyst")).toBeInTheDocument();
      expect(screen.getAllByText("Demo session")).toHaveLength(2);
    });
  });
});
