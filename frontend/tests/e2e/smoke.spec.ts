import { expect, test } from "@playwright/test";

test("login enters the project console", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Secure your AI agents." })).toBeVisible();
  await page.getByRole("button", { name: "Sign In" }).click();
  await expect(page).toHaveURL(/projects\/customer-support-agent/);
  await expect(page.getByRole("heading", { name: "Customer Support Agent" })).toBeVisible();
});

test("policy simulation explains the decision", async ({ page }) => {
  await page.goto("/projects/customer-support-agent/policies");
  await page.getByRole("button", { name: "Run simulation" }).click();
  await expect(page.getByText("Refund exceeds automatic threshold.", { exact: true })).toBeVisible();
  await expect(page.getByText("large-refund", { exact: true })).toHaveCount(2);
});

test("blocked activity opens decision detail", async ({ page }) => {
  await page.goto("/projects/customer-support-agent/activity");
  await page.getByRole("link", { name: "customer.delete" }).click();
  await expect(page.getByText("deny-user-delete", { exact: true })).toBeVisible();
  await expect(page.locator("section").getByText("Destructive customer operation is denied for this project.", { exact: true })).toBeVisible();
});

test("approval can be approved with a comment", async ({ page }) => {
  await page.goto("/projects/customer-support-agent/approvals");
  await page.getByRole("button", { name: "Approve" }).first().click();
  await page.getByPlaceholder("Verified with customer service ticket.").fill("Verified with customer service ticket.");
  await page.getByRole("button", { name: "Approve" }).last().click();
  await expect(page.getByText(/Approved by:/)).toBeVisible();
});

test("replay suite reaches completed state", async ({ page }) => {
  await page.goto("/projects/customer-support-agent/red-team");
  await page.getByRole("button", { name: "Run Replay Suite" }).click();
  await expect(page.getByText("Completed · 105 / 105")).toBeVisible({ timeout: 7000 });
  await expect(page.getByText("98.1%", { exact: true })).toBeVisible();
});
