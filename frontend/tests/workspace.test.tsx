import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "../src/App";

describe("workspace connection", () => {
  it("requires an organization-issued access token before showing financial data", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: /clarity for the decisions that matter/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/secure access token/i)).toHaveAttribute("type", "password");
    expect(screen.queryByText(/reports analyzed/i)).not.toBeInTheDocument();
  });
});
