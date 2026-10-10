// Vite serves the static dashboard in web/. The notebook writes web/data/ directly; the page fetches it at
// runtime (and polls for changes), so data/ is not part of the module graph and is copied as-is on build.
import { cpSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig } from "vite";

const webDir = resolve(import.meta.dirname, "web");
const outDir = resolve(import.meta.dirname, "dist");

const copyData = {
  name: "psll-copy-data",
  apply: "build",
  closeBundle() {
    cpSync(resolve(webDir, "data"), resolve(outDir, "data"), { recursive: true });
  },
};

export default defineConfig({
  root: webDir,
  base: "./",
  publicDir: false,
  plugins: [copyData],
  server: {
    host: true, // listen on the LAN so phones on the same Wi-Fi can open the Network URL
    port: 8000,
    // Notebook output syncs in via Google Drive; the page polls for it, so don't watch it here.
    watch: { ignored: ["**/data/**"] },
  },
  preview: { host: true, port: 8000 },
  build: { outDir, emptyOutDir: true },
});
