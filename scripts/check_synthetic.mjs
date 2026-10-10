// Runs before every `npm run build` (including Cloudflare Pages deploys): refuse to build a public copy
// of real study data. Override only once public release is cleared: PSLL_ALLOW_REAL=1 npm run build
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const manifestPath = resolve(import.meta.dirname, "..", "web", "data", "manifest.json");
const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));

if (!manifest.synthetic && process.env.PSLL_ALLOW_REAL !== "1") {
  console.error(
    "Build refused: web/data contains REAL study data (manifest.synthetic = false), and builds are deployed\n" +
    "publicly. Re-run the notebook with USE_SAMPLE_DATA = True before pushing, or set PSLL_ALLOW_REAL=1\n" +
    "once public release of this data has been cleared."
  );
  process.exit(1);
}
console.log(`Data check passed: ${manifest.synthetic ? "synthetic" : "REAL (PSLL_ALLOW_REAL=1)"} data, generated ${manifest.generated_at}`);
