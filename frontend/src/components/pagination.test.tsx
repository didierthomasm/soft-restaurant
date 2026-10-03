import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Pagination } from "./pagination";

describe("Pagination", () => {
  it("shows the visible range and moves between pages", async () => {
    const onPage = vi.fn();
    render(<Pagination meta={{ total: 65, page: 2, limit: 25 }} label="Incidencias" onPage={onPage} />);
    expect(screen.getByRole("navigation", { name: "Incidencias" })).toHaveTextContent("26–50 de 65");
    await userEvent.click(screen.getByRole("button", { name: "← Anterior" }));
    await userEvent.click(screen.getByRole("button", { name: "Siguiente →" }));
    expect(onPage.mock.calls).toEqual([[1], [3]]);
  });

  it("disables the ends", () => {
    render(<Pagination meta={{ total: 30, page: 1, limit: 25 }} label="RH" onPage={() => undefined} />);
    expect(screen.getByRole("button", { name: "← Anterior" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Siguiente →" })).toBeEnabled();
  });

  it("renders nothing when everything fits", () => {
    const { container } = render(
      <Pagination meta={{ total: 3, page: 1, limit: 25 }} label="RH" onPage={() => undefined} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("sends a page past the end back to the last page", async () => {
    const onPage = vi.fn();
    render(<Pagination meta={{ total: 30, page: 5, limit: 25 }} label="RH" onPage={onPage} />);
    expect(screen.getByRole("navigation", { name: "RH" })).toHaveTextContent("Sin resultados en esta página");
    await userEvent.click(screen.getByRole("button", { name: "← Anterior" }));
    expect(onPage).toHaveBeenCalledWith(2);
  });
});
