import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  timeout: 30_000,
  use: {
    ...devices["Desktop Chrome"],
    channel: "chrome",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "mock",
      testMatch: /demo.spec.ts/,
      use: { baseURL: "http://127.0.0.1:5173" },
    },
    {
      name: "live-contract",
      testMatch: /live.spec.ts/,
      use: { baseURL: "http://127.0.0.1:5174" },
    },
  ],
  webServer: [
    {
      command: "npm run dev",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: !process.env.CI,
      env: { VITE_ORCHESTRATOR_URL: "" },
    },
    {
      command: "npm run dev -- --port 5174",
      url: "http://127.0.0.1:5174",
      reuseExistingServer: !process.env.CI,
      env: { VITE_ORCHESTRATOR_URL: "http://127.0.0.1:8000" },
    },
  ],
});
