import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  retries: 1,
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3001',
    headless: true,
    launchOptions: {
      // Chromium complet (évite le headless-shell dont le pipe crashe sous Nix).
      executablePath: process.env.PW_CHROMIUM_EXECUTABLE
        || '/home/user/.cache/ms-playwright/chromium-1254/chrome-linux64/chrome',
      args: [
        '--disable-gpu',
        '--disable-software-rasterizer',
        '--disable-dev-shm-usage',
      ],
    },
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
  ],
});
