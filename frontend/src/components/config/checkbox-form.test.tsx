import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, expect, test, vi } from "vitest";

import { Checkbox } from "@/components/ui/checkbox";

beforeAll(() => {
  // jsdom has no ResizeObserver; Radix Checkbox's bubble input sizing needs one.
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
});

test("Radix Checkbox with name/value contributes to FormData when checked", async () => {
  render(
    <form aria-label="f">
      <Checkbox name="sr_id" value="7" defaultChecked aria-label="a" />
      <Checkbox name="sr_id" value="8" aria-label="b" />
      <Checkbox name="sr_id" value="9" aria-label="c" />
    </form>,
  );
  await userEvent.click(screen.getByLabelText("c"));
  const data = new FormData(screen.getByRole("form") as HTMLFormElement);
  expect(data.getAll("sr_id")).toEqual(["7", "9"]);
});
