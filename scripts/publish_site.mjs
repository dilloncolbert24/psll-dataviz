// Copy the dashboard (web/) into the personal site so it is served at <site>/psll/.
//   npm run publish:site                 # synthetic data only (default)
//   npm run publish:site -- --allow-real # also publish real study data — only once public release is cleared
// Target defaults to ~/Developer/personalSite; override with PSLL_SITE_DIR.
import { cpSync, existsSync, readFileSync, rmSync } from "node:fs";
import { homedir } from "node:os";
import { basename, join, resolve } from "node:path";

const webDir = resolve(import.meta.dirname, "..", "web");
const siteDir = process.env.PSLL_SITE_DIR ?? join(homedir(), "Developer", "personalSite");
const target = join(siteDir, "public", "psll");
const allowReal = process.argv.includes("--allow-real");

if (!existsSync(join(siteDir, "package.json"))) {
  console.error(`Personal site not found at ${siteDir} (set PSLL_SITE_DIR).`);
  process.exit(1);
}

const manifest = JSON.parse(readFileSync(join(webDir, "data", "manifest.json"), "utf8"));
if (!manifest.synthetic && !allowReal) {
  console.error(
    "Refusing to publish: web/data contains REAL study data (manifest.synthetic = false).\n" +
    "The personal site repo and website are public. Re-run with --allow-real only once public release\n" +
    "of this data has been cleared. Nothing was copied."
  );
  process.exit(1);
}

rmSync(target, { recursive: true, force: true });
cpSync(webDir, target, {
  recursive: true,
  filter: (src) => basename(src) !== ".DS_Store",
});

console.log(`Published ${manifest.synthetic ? "SYNTHETIC" : "REAL"} data (generated ${manifest.generated_at})`);
console.log(`  ${webDir}\n  → ${target}`);
console.log("Next: in personalSite, commit public/psll and push to deploy.");
