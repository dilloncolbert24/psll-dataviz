// Cloudflare Pages runs `npm run build` and deploys `dist/`.
// The visualization is one self-contained HTML file, so the build just copies public/ to dist/.
import { cpSync, rmSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const src = resolve(root, "public");
const out = resolve(root, "dist");

rmSync(out, { recursive: true, force: true });
cpSync(src, out, { recursive: true });
console.log("Copied public/ -> dist/");
