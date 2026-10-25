import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { expect, test } from "@playwright/test";

const python = process.platform === "win32" ? "backend/.venv/Scripts/python.exe" : "backend/.venv/bin/python";
const email = `e2e-${randomUUID()}@example.com`;
const password = randomUUID();
const api = "http://127.0.0.1:8001";
const origin = { Origin: "http://127.0.0.1:3010" };

test.beforeAll(() => {
  execFileSync(python, ["-c", `
import json, sys
sys.path.insert(0, 'backend')
from app.auth import passwords
from app.db import SessionLocal
from app.models import Tenant, User, TenantMember
email, password = json.load(sys.stdin)
with SessionLocal() as db:
    tenant = Tenant(name='Browser test')
    user = User(email=email, password_hash=passwords.hash(password))
    db.add_all([tenant, user])
    db.flush()
    db.add(TenantMember(user_id=user.id, tenant_id=tenant.id, role='admin'))
    db.commit()
`], { input: JSON.stringify([email, password]), env: { ...process.env, AG_DATABASE_URL: process.env.AG_TEST_DATABASE_URL }, stdio: ["pipe", "pipe", "pipe"] });
});

test("console uses real auth, project settings, keys, policies, approvals, audit and replay", async ({ page }) => {
  const browserErrors: string[] = [];
  page.on("pageerror", (error) => browserErrors.push(error.message));
  await page.goto("/login");
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole("button", { name: "Sign In" }).click();
  await expect(page).toHaveURL(/\/projects$/);
  await page.getByRole("button", { name: "Create Project" }).click();
  await page.getByPlaceholder("Customer Support Agent").fill("Browser Project");
  await page.getByLabel("Provider", { exact: true }).fill("Mock");
  await page.getByLabel("Default Model", { exact: true }).fill("mock-model");
  await page.getByRole("button", { name: "Create Project", exact: true }).click();
  await page.getByRole("link", { name: "Browser Project", exact: true }).click();
  await expect(page).toHaveURL(/\/projects\/proj_/);
  const projectId = new URL(page.url()).pathname.split("/")[2];
  await expect(page.getByRole("heading", { name: "Browser Project" })).toBeVisible();
  await expect(page.getByText("Not verified", { exact: true })).toBeVisible();

  await page.goto(`/projects/${projectId}/settings`);
  await page.getByLabel("Project name", { exact: true }).fill("Updated Browser Project");
  await page.getByRole("button", { name: "Save settings" }).click();
  await expect(page.getByRole("status")).toHaveText("[+] Settings saved");
  await page.reload();
  await expect(page.getByLabel("Project name", { exact: true })).toHaveValue("Updated Browser Project");

  await page.goto(`/projects/${projectId}/api-keys`);
  await page.getByRole("button", { name: /Create API Key/i }).click();
  await page.getByRole("dialog").getByLabel("Name", { exact: true }).fill("Browser key");
  await page.getByRole("button", { name: "Create key", exact: true }).click();
  const rawKey = await page.getByRole("dialog").locator(".break-all").innerText();
  expect(rawKey).toMatch(/^ag_live_/);
  await page.getByRole("button", { name: "I saved it" }).click();

  const tool = await page.request.put(`${api}/v1/console/projects/${projectId}/tools/payment.refund`, { headers: origin, data: { name: "payment.refund" } });
  expect(tool.ok()).toBeTruthy();
  await page.goto(`/projects/${projectId}/policies`);
  await page.getByRole("button", { name: "Publish rule" }).click();
  await expect(page.getByText("payment.refund", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Run simulation" }).click();
  await expect(page.getByText("APPROVAL", { exact: true })).toHaveCount(2);
  const authorize = await page.request.post(`${api}/v1/tools/authorize`, { headers: { ...origin, Authorization: `Bearer ${rawKey}` }, data: { tool: "payment.refund", arguments: { amount: 1000000 } } });
  expect(authorize.ok()).toBeTruthy();
  await page.goto(`/projects/${projectId}/approvals`);
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await page.getByPlaceholder("Verified with customer service ticket.").fill("Browser verification");
  await page.getByRole("dialog").getByRole("button", { name: "Approve", exact: true }).click();
  await expect(page.getByText(`Approved by: ${email}`)).toBeVisible();

  const chat = await page.request.post(`${api}/v1/chat/completions`, { headers: { ...origin, Authorization: `Bearer ${rawKey}` }, data: { model: "mock-model", messages: [{ role: "user", content: "Hello alice@example.com" }] } });
  expect(chat.ok()).toBeTruthy();
  await page.goto(`/projects/${projectId}`);
  await page.getByRole("button", { name: "Verify Audit Chain" }).click();
  await expect(page.getByText("[+] Hash Chain Valid", { exact: true })).toBeVisible();

  const attack = await page.request.post(`${api}/v1/attack-cases`, { headers: origin, data: { projectId, name: "Refund needs approval", input: { tool: "payment.refund", arguments: { amount: 1000000 } }, expected_tool: "payment.refund", expected_decision: "REQUIRE_APPROVAL" } });
  expect(attack.ok()).toBeTruthy();
  await page.goto(`/projects/${projectId}/red-team`);
  await page.getByRole("button", { name: "Run Replay Suite" }).click();
  await expect(page.getByText("queued", { exact: true })).toBeVisible();
  execFileSync(python, ["-c", "import sys; sys.path.insert(0, 'backend'); from app.db import SessionLocal; from app.replay import run_one; db=SessionLocal(); run_one(db); db.close()"], { env: { ...process.env, AG_DATABASE_URL: process.env.AG_TEST_DATABASE_URL } });
  await expect(page.getByText("Completed · 1 / 1")).toBeVisible();
  await expect(page.getByText("[+] PASS", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect((await page.request.get(`${api}/v1/console/auth/session`)).status()).toBe(401);
  expect(browserErrors).toEqual([]);
});
