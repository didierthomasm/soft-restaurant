import { expect, test } from "@playwright/test";

const USER = process.env.FAKE_AUTH_USER ?? "demo";
const PASSWORD = process.env.FAKE_AUTH_PASSWORD ?? "demo";

test("generate, read and approve the weekly draft", async ({ page }) => {
  test.setTimeout(120_000);

  await page.goto("/revision?desde=2026-09-21");
  await page.getByLabel("Usuario").fill(USER);
  await page.getByLabel("Contraseña").fill(PASSWORD);
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/revision\?desde=2026-09-21/);

  // First run creates the draft; later runs (the demo DB persists) regenerate it.
  const generate = page.getByRole("button", { name: "Generar borrador" });
  const regenerate = page.getByRole("button", { name: "Generar de nuevo" });
  await expect(generate.or(regenerate)).toBeVisible();
  await ((await generate.isVisible()) ? generate : regenerate).click();

  // The worker polls every 10 s; the page polls every 3 s.
  await expect(page.getByRole("status").filter({ hasText: "Generando borrador" })).toBeVisible();
  await expect(page.getByText(/Borrador de demostración/)).toBeVisible({ timeout: 45_000 });
  await expect(page.getByRole("heading", { name: "Lista para RH" })).toBeVisible();

  // Deep link: a finding action opens the day panel on /semana.
  const link = page.locator('a[href^="/semana?"]').first();
  await expect(link).toBeVisible();
  const href = await link.getAttribute("href");
  expect(href).toMatch(/empleado=\d+/);
  expect(href).toMatch(/dia=/);

  await page.goto(href as string);
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();

  await page.goto((href as string).replace(/empleado=\d+/, "empleado=999"));
  await expect(page.getByRole("row", { name: /EMPLEADO A/ })).toBeVisible();
  await expect(page.getByRole("dialog")).toHaveCount(0);

  await page.goto("/revision?desde=2026-09-21");
  await page.getByRole("button", { name: "Aprobar" }).click();
  await expect(page.getByText("Borrador aprobado", { exact: true })).toBeVisible();
  await expect(page.getByText(/· aprobado el \d{2}\/\d{2}\/\d{4}/)).toBeVisible();
});
