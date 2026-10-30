import { defineConfig } from "@playwright/test";

/**
 * Screenshot run for docs/design/screens (Step 5A).
 *
 * Needs a running frontend and a backend started with LLM_PROVIDER=scripted
 * and an empty DATABASE_URL, so every run starts from the same seeded demo
 * requests and the same recorded outputs. See docs/design/SCREENSHOTS.md.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,
  reporter: [["list"]],
  use: {
    baseURL: process.env.SCREENS_BASE_URL ?? "http://localhost:3010",
    locale: "ar-SA",
    timezoneId: "Asia/Riyadh",
  },
});
