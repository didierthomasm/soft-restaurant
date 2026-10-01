import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";

import { FormError, QueryError } from "./feedback";

describe("QueryError", () => {
  it("shows the backend message and retries", async () => {
    const onRetry = vi.fn();
    const error = new ApiError("SR_UNAVAILABLE", "No se pudo leer SoftRestaurant. Revisa Tailscale.", 503);
    render(<QueryError error={error} onRetry={onRetry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Revisa Tailscale");
    await userEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("hides details of unexpected errors", () => {
    render(<QueryError error={new Error("stack trace")} onRetry={() => undefined} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Ocurrió un error inesperado");
  });
});

describe("FormError", () => {
  it("renders nothing without error", () => {
    const { container } = render(<FormError error={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
