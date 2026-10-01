import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ReviewDetailOut } from "@/lib/api/types";

import { ReviewDetail } from "./review-detail";

const approve = vi.fn();

vi.mock("@/lib/api/reviews", () => ({
  useApproveReview: () => ({ mutate: approve, error: null, isPending: false }),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const ABSENT = "ABSENT_NO_EXCEPTION:7:2026-09-23";
const CONFIG = "CONFIG_WARNING/MISSING_RH_NAME:7:-";

function review(overrides: Partial<ReviewDetailOut> = {}): ReviewDetailOut {
  return {
    id: 5,
    year: 2026,
    week: 39,
    trigger: "THURSDAY",
    status: "READY",
    created_at: "2026-09-24T23:30:00Z",
    as_of: "2026-09-24T17:30:00",
    approved_at: null,
    error: null,
    findings: [
      { id: ABSENT, kind: "ABSENT_NO_EXCEPTION", employee_id: 7, employee_name: "EMPLEADO G", days: ["2026-09-23"], facts: {} },
      { id: CONFIG, kind: "CONFIG_WARNING", employee_id: 7, employee_name: "EMPLEADO G", days: [], facts: { code: "MISSING_RH_NAME", occurrences: 1 } },
    ],
    narrative: {
      summary: "Una falta de EMPLEADO G sin justificar.",
      items: [
        { finding_id: ABSENT, priority: "HIGH", explanation: "EMPLEADO G faltó el miércoles.", suggested_action: "JUSTIFY" },
        { finding_id: CONFIG, priority: "LOW", explanation: "Falta su nombre en RH.", suggested_action: "FIX_CONFIG" },
      ],
    },
    rh_rows: [{ employee_id: 7, name: "EMPLEADO G", day: "2026-09-23", rh_type: "FALTA_INJUSTIFICADA", comment: "" }],
    model: "claude-opus-5-5",
    input_tokens: 900,
    output_tokens: 150,
    stale: false,
    ...overrides,
  };
}

function renderDetail(data: ReviewDetailOut, onRegenerate = vi.fn()) {
  render(<ReviewDetail review={data} weekMonday="2026-09-21" onRegenerate={onRegenerate} regenerating={false} />);
  return onRegenerate;
}

describe("ReviewDetail", () => {
  beforeEach(() => approve.mockReset());

  it("shows the summary and findings grouped by priority with their actions", () => {
    renderDetail(review());
    expect(screen.getByText("Una falta de EMPLEADO G sin justificar.")).toBeInTheDocument();
    const high = screen.getByRole("region", { name: "Prioridad alta" });
    expect(within(high).getByText("EMPLEADO G faltó el miércoles.")).toBeInTheDocument();
    expect(within(high).getByRole("link", { name: "Justificar" })).toHaveAttribute(
      "href",
      "/semana?desde=2026-09-21&empleado=7&dia=2026-09-23",
    );
    const low = screen.getByRole("region", { name: "Prioridad baja" });
    expect(within(low).getByText(/Falta nombre en RH · 1 veces/)).toBeInTheDocument();
    expect(within(low).getByRole("link", { name: "Corregir configuración" })).toHaveAttribute(
      "href",
      "/configuracion",
    );
  });

  it("lists the RH rows", () => {
    renderDetail(review());
    expect(screen.getByRole("heading", { name: "Lista para RH" })).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /EMPLEADO G/ })).toHaveTextContent("Falta injustificada");
  });

  it("shows findings and the reason when there is no narrative", () => {
    // Review Focus #3
    renderDetail(review({ status: "READY_NO_NARRATIVE", narrative: null, error: "Falta ANTHROPIC_API_KEY" }));
    expect(screen.getByRole("status")).toHaveTextContent(/no pudo redactar.*Falta ANTHROPIC_API_KEY/);
    const all = screen.getByRole("region", { name: "Hallazgos" });
    expect(within(all).getByRole("link", { name: "Ver día" })).toBeInTheDocument();
    expect(within(all).getByRole("link", { name: "Ir a configuración" })).toBeInTheDocument();
  });

  it("warns when the data changed", () => {
    renderDetail(review({ stale: true }));
    expect(screen.getByRole("status")).toHaveTextContent("Los datos cambiaron desde este borrador");
  });

  it("approves a ready draft and regenerates", async () => {
    const onRegenerate = renderDetail(review());
    await userEvent.click(screen.getByRole("button", { name: "Aprobar" }));
    expect(approve).toHaveBeenCalledWith(5, expect.anything());
    await userEvent.click(screen.getByRole("button", { name: "Generar de nuevo" }));
    expect(onRegenerate).toHaveBeenCalled();
  });

  it("shows when it was approved and hides the approve button", () => {
    renderDetail(review({ status: "APPROVED", approved_at: "2026-09-24T18:05:00" }));
    expect(screen.queryByRole("button", { name: "Aprobar" })).not.toBeInTheDocument();
    expect(screen.getByText(/aprobado el 24\/09\/2026 18:05/)).toBeInTheDocument();
  });

  it("says when the week has no findings", () => {
    renderDetail(review({ findings: [], narrative: { summary: "Semana sin pendientes.", items: [] }, rh_rows: [] }));
    expect(screen.getByText("Sin hallazgos esta semana.")).toBeInTheDocument();
  });
});
