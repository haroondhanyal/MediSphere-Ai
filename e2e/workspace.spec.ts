import { expect, test } from "@playwright/test";

test("sign in and open remote monitoring", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("img", { name: "MediSphere AI" })).toBeVisible();
  await page.getByLabel("Email address").fill(process.env.DEMO_EMAIL ?? "admin@medisphere.local");
  await page.getByLabel("Password").fill(process.env.DEMO_PASSWORD ?? "MediSphere-Demo-2026!");
  await page.getByLabel("Organization").fill("medisphere-health");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/dashboard/);
  await expect(page.getByRole("heading", { name: "Workspace modules" })).toBeVisible();
  await expect(page.getByText("Phases 1–10 local workflows are ready")).toBeVisible();
  await page.getByRole("link", { name: "Remote monitoring", exact: true }).last().click();
  await expect(page.getByRole("heading", { name: "Remote patient monitoring" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Alert thresholds" })).toBeVisible();
});
