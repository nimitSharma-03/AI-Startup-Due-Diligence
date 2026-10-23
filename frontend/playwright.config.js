import { defineConfig, devices } from '@playwright/test'

// By default the suite starts the production stack (Gunicorn serving the API
// and the built frontend). Set E2E_BASE_URL to run it against a deployment.
const external = process.env.E2E_BASE_URL
const port = process.env.E2E_PORT || '8001'

export default defineConfig({
  testDir: './e2e',
  timeout: 90_000,
  expect: { timeout: 30_000 },
  fullyParallel: false,
  workers: 1,
  retries: external ? 1 : 0,
  reporter: [['list']],
  use: {
    baseURL: external || `http://127.0.0.1:${port}`,
    acceptDownloads: true,
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1366, height: 900 } }, testIgnore: /mobile\.spec\.js/ },
    { name: 'mobile', use: { ...devices['Pixel 7'] }, testMatch: /mobile\.spec\.js/ },
  ],
  webServer: external
    ? undefined
    : {
        command: `cd .. && .venv/bin/gunicorn app:app --bind 127.0.0.1:${port} --workers 1 --threads 4 --timeout 120`,
        url: `http://127.0.0.1:${port}/api/health`,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
})
