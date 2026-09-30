#!/usr/bin/env node
/**
 * Regenerate landing/public/images/og.png — the 1200×630 social preview card.
 *
 *   npm --prefix landing run og
 *
 * Renders scripts/og.html with headless Chromium (playwright-core from the
 * frontend workspace — run `npm --prefix frontend ci` first). Re-run it
 * whenever the app UI shown on the card changes, like the other screenshots.
 */
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.join(here, "..", "..");
const require = createRequire(path.join(repoRoot, "frontend", "package.json"));

let chromium;
try {
  ({ chromium } = require("playwright-core"));
} catch {
  console.error("playwright-core not found — run: npm --prefix frontend ci");
  process.exit(1);
}

const browser = await chromium.launch({
  args: ["--allow-file-access-from-files"],
});
const page = await browser.newPage({
  viewport: { width: 1200, height: 630 },
  deviceScaleFactor: 2,
});
await page.goto(`file://${path.join(here, "og.html")}`);
await page.evaluate(() => document.fonts.ready);
const out = path.join(here, "..", "public", "images", "og.png");
await page.screenshot({ path: out });
await browser.close();
console.log(`og.png written: ${path.relative(repoRoot, out)}`);
