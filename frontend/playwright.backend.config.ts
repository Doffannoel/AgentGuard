import { defineConfig, devices } from "@playwright/test";
import { resolve } from "node:path";

const database = process.env.AG_TEST_DATABASE_URL;
if (!database) throw new Error("Set AG_TEST_DATABASE_URL to a disposable PostgreSQL database.");
const python = resolve(process.platform === "win32" ? "backend/.venv/Scripts/python.exe" : "backend/.venv/bin/python");

export default defineConfig({
  testDir: "./tests/backend-e2e",
  workers: 1,
  timeout: 60000,
  use: { baseURL: "http://127.0.0.1:3010", trace: "retain-on-failure" },
  webServer: [
    {
      command: `"${python}" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001 --no-access-log`,
      url: "http://127.0.0.1:8001/health",
      env: { AG_DATABASE_URL: database, AG_CONSOLE_ORIGINS: '["http://127.0.0.1:3010"]' }
    },
    {
      command: "npm run dev -- --hostname 127.0.0.1 --port 3010",
      url: "http://127.0.0.1:3010",
      env: { NEXT_PUBLIC_AGENTGUARD_API_URL: "http://127.0.0.1:8001", NEXT_DIST_DIR: ".next-backend-e2e" }
    }
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }]
});
