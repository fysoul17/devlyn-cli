// Playwright config used only by browser-validate benchmark fixtures.
// Runs against web/index.html served via `npx serve web` (fixture setup.sh
// starts the server). Keep config minimal.
module.exports = {
  testDir: './tests/e2e',
  timeout: 30_000,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    headless: true,
  },
  webServer: {
    command: 'npx --yes serve -l 5173 web',
    port: 5173,
    reuseExistingServer: !process.env.CI,
    timeout: 15_000,
  },
};
