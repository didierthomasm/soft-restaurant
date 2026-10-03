import { expect, type Page, test } from "@playwright/test";

const USER = process.env.FAKE_AUTH_USER ?? "demo";
const PASSWORD = process.env.FAKE_AUTH_PASSWORD ?? "demo";

async function login(page: Page, path: string) {
  await page.goto(path);
  await expect(page).toHaveURL(/\/login\?next=/);
  await page.getByLabel("Usuario").fill(USER);
  await page.getByLabel("Contraseña").fill(PASSWORD);
  await page.getByRole("button", { name: "Entrar" }).click();
}

test("login through a legacy week link, justify an incident and export", async ({ page }) => {
  await login(page, "/semana?desde=2026-09-21");
  await expect(page).toHaveURL(/\/calendario\?vista=semana&desde=2026-09-21/);
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

test("create, edit and delete an absence exception from the calendar", async ({ page }) => {
  await login(page, "/calendario?vista=semana&desde=2026-09-21");
  const cell = page.getByRole("row", { name: /EMPLEADO A/ }).getByRole("button", { name: /lun 21\/09/ });

  await cell.click();
  await page.getByLabel("Comentario").fill("E2E vacaciones");
  await page.getByRole("button", { name: "Guardar excepción" }).click();
  await expect(page.getByText("Excepción registrada")).toBeVisible();

  await cell.click();
  const panel = page.getByRole("dialog");
  await expect(panel.getByRole("heading", { name: "Excepción · Ausencia justificada" })).toBeVisible();
  await expect(panel.getByLabel("Comentario")).toHaveValue("E2E vacaciones");
  await expect(panel.getByRole("heading", { name: "Agregar excepción" })).toHaveCount(0);
  await panel.getByLabel("Tipo en RH").selectOption("INCAPACIDAD");
  await panel.getByRole("button", { name: "Guardar cambios" }).click();
  await expect(page.getByText("Excepción actualizada")).toBeVisible();

  await cell.click();
  await expect(page.getByRole("dialog").getByLabel("Tipo en RH")).toHaveValue("INCAPACIDAD");
  await page.getByRole("button", { name: "Eliminar excepción" }).click();
  await page.getByRole("button", { name: /Confirmar/ }).click();
  await expect(page.getByText("Excepción eliminada")).toBeVisible();
});

test("filter incidents by employee and page through them", async ({ page }) => {
  await login(page, "/incidencias?desde=2026-09-01&hasta=2026-09-30");
  const pages = page.getByRole("navigation", { name: "Páginas de incidencias" });
  await expect(pages).toContainText(/^1–25 de \d+/);
  await pages.getByRole("button", { name: "Siguiente →" }).click();
  await expect(page).toHaveURL(/pag=2/);
  await expect(pages).toContainText(/^26–/);

  await page.getByLabel("Empleado").selectOption({ label: "EMPLEADO A" });
  await page.getByRole("button", { name: "Ver" }).click();
  await expect(page).toHaveURL(/empleado=\d+/);
  await expect(page).not.toHaveURL(/pag=/);
  await page.reload();
  await expect(page.getByLabel("Empleado")).not.toHaveValue("");
  const rows = page
    .getByRole("heading", { name: "Todas las incidencias" })
    .locator("xpath=..")
    .getByRole("row")
    .filter({ hasNot: page.getByRole("columnheader") });
  for (const row of await rows.all()) await expect(row).toContainText("EMPLEADO A");
});

test("switch from week to month and open a day", async ({ page }) => {
  await login(page, "/calendario?vista=semana&desde=2026-09-21");
  await page.getByRole("link", { name: "Mes" }).click();
  await expect(page).toHaveURL(/vista=mes&mes=2026-09/);
  await page.getByRole("row", { name: /EMPLEADO A/ }).getByRole("button", { name: /lun 21\/09/ }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
});

test("the API rejects requests without a session", async ({ request }) => {
  const response = await request.get("/backend/attendance/calendar?from=2026-09-21&to=2026-09-27");
  expect(response.status()).toBe(401);
});
