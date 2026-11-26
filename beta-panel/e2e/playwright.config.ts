import { defineConfig, devices } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

function loadEnvFile(): void {
  const envPath = process.env.BETA01B_E2E_ENV_FILE;
  if (!envPath) return;
  const text = fs.readFileSync(envPath, "utf8");
  for (const line of text.split("\n")) {
    if (!line || line.startsWith("#") || !line.includes("=")) continue;
    const idx = line.indexOf("=");
    const key = line.slice(0, idx);
    const value = line.slice(idx + 1);
    if (!process.env[key]) process.env[key] = value;
  }
}

loadEnvFile();

const baseURL = process.env.BETA01B_PANEL_BASE_URL;
if (!baseURL) {
  throw new Error("BETA01B_PANEL_BASE_URL is required for browser E2E");
}

const artifactDir = process.env.BETA01B_ARTIFACT_DIR || path.join(process.cwd(), "test-results");

export default defineConfig({
  testDir: "./",
  testMatch: /.*\.spec\.ts/,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 180_000,
  expect: { timeout: 30_000 },
  reporter: [
    ["list"],
    ["junit", { outputFile: path.join(artifactDir, "playwright-junit.xml") }],
  ],
  use: {
    baseURL,
    headless: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    ignoreHTTPSErrors: false,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  outputDir: path.join(artifactDir, "playwright-output"),
});
