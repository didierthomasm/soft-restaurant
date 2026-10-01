import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ReviewDetailOut, ReviewSummaryOut } from "@/lib/api/types";
import { todayIso, weekStart } from "@/lib/dates";

import { ReviewView, WeekReviews } from "./review-view";

const create = vi.fn();
const replace = vi.fn();
const state: {
  list: ReviewSummaryOut[];
  detail: ReviewDetailOut | undefined;
  recent: { data: ReviewSummaryOut[] | undefined; isPending: boolean };
} = {
  list: [],
  detail: undefined,
  recent: { data: [], isPending: false },
};

vi.mock("@/lib/api/reviews", () => ({
  useWeekReviews: () => ({ data: state.list, isPending: false, isError: false }),
  useRecentReviews: () => state.recent,
  useReview: () => ({ data: state.detail, isPending: state.detail === undefined, isError: false }),
  useCreateReview: () => ({ mutate: create, error: null, isPending: false }),
  useApproveReview: () => ({ mutate: vi.fn(), error: null, isPending: false }),
}));
vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: ReactNode }) => <a href={href}>{children}</a>,
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }) }));

function summary(overrides: Partial<ReviewSummaryOut> = {}): ReviewSummaryOut {
  return {
    id: 5,
    year: 2026,
    week: 39,
    trigger: "MANUAL",
    status: "READY",
    created_at: "2026-09-24T23:30:00Z",
    as_of: "2026-09-24T17:30:00",
    approved_at: null,
    error: null,
    ...overrides,
  };
}

function detail(overrides: Partial<ReviewDetailOut> = {}): ReviewDetailOut {
  return {
    ...summary(),
    findings: [],
    narrative: { summary: "Semana sin pendientes.", items: [] },
    rh_rows: [],
    model: "fake",
    input_tokens: 0,
    output_tokens: 0,
    stale: false,
    ...overrides,
  };
}

beforeEach(() => {
  create.mockReset();
  replace.mockReset();
  state.list = [];
  state.detail = undefined;
  state.recent = { data: [], isPending: false };
});

describe("ReviewView", () => {
  it("opens the week of the newest draft when no week is requested", () => {
    state.recent = { data: [summary({ year: 2026, week: 39 })], isPending: false };
    render(<ReviewView requestedStart={null} />);
    expect(replace).toHaveBeenCalledWith("/revision?desde=2026-09-21");
  });

  it("opens the current week when there are no drafts", () => {
    render(<ReviewView requestedStart={null} />);
    expect(replace).toHaveBeenCalledWith(`/revision?desde=${weekStart(todayIso())}`);
  });

  it("waits for the recent drafts before redirecting", () => {
    state.recent = { data: undefined, isPending: true };
    render(<ReviewView requestedStart={null} />);
    expect(replace).not.toHaveBeenCalled();
  });

  it("shows the requested week without redirecting", () => {
    render(<ReviewView requestedStart="2026-09-23" />);
    expect(replace).not.toHaveBeenCalled();
    expect(screen.getByText(/Semana 39 · 21\/09\/2026/)).toBeInTheDocument();
  });
});

describe("WeekReviews", () => {
  it("offers to generate the first draft of the week", async () => {
    render(<WeekReviews monday="2026-09-21" />);
    expect(screen.getByText("Todavía no hay borrador para esta semana.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Generar borrador" }));
    expect(create).toHaveBeenCalledWith({ year: 2026, week: 39 }, expect.anything());
  });

  it("asks for ISO week 53 of 2026 at the end of December", async () => {
    // Review Focus #5
    render(<WeekReviews monday="2026-12-28" />);
    await userEvent.click(screen.getByRole("button", { name: "Generar borrador" }));
    expect(create).toHaveBeenCalledWith({ year: 2026, week: 53 }, expect.anything());
  });

  it("shows progress while the draft is generated", () => {
    state.list = [summary({ status: "RUNNING", as_of: null })];
    render(<WeekReviews monday="2026-09-21" />);
    expect(screen.getByRole("status")).toHaveTextContent("Generando borrador");
  });

  it("trusts the detail when the list is behind", () => {
    // Review Focus #2
    state.list = [summary({ status: "RUNNING" })];
    state.detail = detail();
    render(<WeekReviews monday="2026-09-21" />);
    expect(screen.getByText("Semana sin pendientes.")).toBeInTheDocument();
  });

  it("explains a failed run and lets the manager retry", async () => {
    state.list = [summary({ status: "FAILED", error: "No se pudo leer SoftRestaurant. Revisa Tailscale." })];
    state.detail = detail({ status: "FAILED", narrative: null, error: "No se pudo leer SoftRestaurant. Revisa Tailscale." });
    render(<WeekReviews monday="2026-09-21" />);
    expect(screen.getByRole("alert")).toHaveTextContent("No se pudo leer SoftRestaurant");
    await userEvent.click(screen.getByRole("button", { name: "Intentar de nuevo" }));
    expect(create).toHaveBeenCalled();
  });

  it("lists earlier drafts of the week", () => {
    state.list = [summary({ id: 6 }), summary({ id: 5, trigger: "THURSDAY", status: "APPROVED" })];
    state.detail = detail({ id: 6 });
    render(<WeekReviews monday="2026-09-21" />);
    expect(screen.getByText("Borradores anteriores de esta semana (1)")).toBeInTheDocument();
    expect(screen.getByText(/Jueves · Aprobado · datos al 24\/09\/2026 17:30/)).toBeInTheDocument();
  });
});
