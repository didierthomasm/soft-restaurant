import { expect, test } from "@playwright/test";

const USER = process.env.FAKE_AUTH_USER ?? "demo";
const PASSWORD = process.env.FAKE_AUTH_PASSWORD ?? "demo";

test("login, review the week, justify an incident and export", async ({ page }) => {
  await page.goto("/semana?desde=2026-09-21");
  await expect(page).toHaveURL(/\/login\?next=/);

  await page.getByLabel("Usuario").fill(USER);
  await page.getByLabel("Contraseña").fill(PASSWORD);
  await page.getByRole("button", { name: "Entrar" }).click();

  await expect(page).toHaveURL(/\/semana\?desde=2026-09-21/);
  await expect(page.getByRole("row", { name: /EMPLEADO A/ })).toBeVisible();

  await page.goto("/incidencias?desde=2026-09-01&hasta=2026-09-27");
  await expect(page.getByRole("heading", { name: "Para capturar en RH" })).toBeVisible();
  await page.getByRole("button", { name: "Justificar" }).first().click();
  await page.getByLabel("Motivo").fill("Prueba E2E");
  await page.getByRole("button", { name: "Guardar justificación" }).click();
  await expect(page.getByText("Justificación guardada")).toBeVisible();

  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Exportar a Excel" }).click();
  expect((await download).suggestedFilename()).toBe("asistencia_2026-09-01_2026-09-27.xlsx");
});

test("the API rejects requests without a session", async ({ request }) => {
  const response = await request.get("/backend/attendance/calendar?from=2026-09-21&to=2026-09-27");
  expect(response.status()).toBe(401);
});
