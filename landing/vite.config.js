import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The landing imports the app's design tokens (single source of truth),
// so the dev server must be allowed to read outside this package.
const repoRoot = fileURLToPath(new URL("..", import.meta.url));

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    fs: { allow: [repoRoot] },
  },
  test: {
    environment: "jsdom",
    environmentOptions: {
      jsdom: { url: "http://localhost" },
    },
    globals: true,
    setupFiles: ["./src/test/setup.js"],
    css: false,
  },
});
