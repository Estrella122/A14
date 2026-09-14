import { defineConfig, devices } from '@playwright/test'
import { existsSync } from 'node:fs'

const localChrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const launchOptions = !process.env.CI && existsSync(localChrome) ? { executablePath: localChrome } : {}

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [['html', { open: 'never' }], ['list']] : 'list',
  use: {
    baseURL: 'http://127.0.0.1:5176',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    launchOptions,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile-chromium', use: { ...devices['Pixel 7'] } },
  ],
  webServer: {
    command: 'npm --prefix .. run dev',
    url: 'http://127.0.0.1:5176/overview/',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})
