// Build the public landing page as plain static files in `out/` for hosts that
// cannot run Node.js (for example InfinityFree). See docs/DEPLOY_INFINITYFREE.md.
//
// Usage (from apps/web):  npm run build:static
// Optional:               set NEXT_PUBLIC_SITE_URL=https://your-domain first

import { spawnSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, extname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const outDir = join(webRoot, "out");
const require = createRequire(import.meta.url);

function fail(message) {
  console.error(`\n[build:static] ${message}`);
  process.exit(1);
}

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL?.trim();
if (siteUrl) {
  let parsed;
  try {
    parsed = new URL(siteUrl);
  } catch {
    fail(`NEXT_PUBLIC_SITE_URL is not a valid absolute URL: ${siteUrl}`);
  }
  if (!/^https?:$/.test(parsed.protocol)) fail("NEXT_PUBLIC_SITE_URL must start with http:// or https://");
  if (/^(localhost|127\.|\[::1\])/.test(parsed.hostname)) fail("NEXT_PUBLIC_SITE_URL must be the public domain, not localhost.");
  console.log(`[build:static] Sharing metadata will use ${parsed.origin}`);
} else {
  console.warn(
    "[build:static] NEXT_PUBLIC_SITE_URL is not set. The site works, but social-sharing image tags are omitted.\n" +
      "                Set it to the final public URL and rebuild before publishing.",
  );
}

rmSync(outDir, { recursive: true, force: true });

const nextBin = require.resolve("next/dist/bin/next");
const result = spawnSync(process.execPath, [nextBin, "build"], {
  cwd: webRoot,
  stdio: "inherit",
  env: { ...process.env, NEXT_STATIC_EXPORT: "1", NEXT_TELEMETRY_DISABLED: "1" },
});
if (result.status !== 0) fail("next build failed.");
if (!existsSync(join(outDir, "index.html"))) fail("Static export did not produce out/index.html.");

// Apache (InfinityFree) serves this page for unknown paths.
writeFileSync(join(outDir, ".htaccess"), "ErrorDocument 404 /404.html\n");

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? walk(path) : [path];
  });
}

const files = walk(outDir);
const problems = [];
for (const file of files) {
  const ext = extname(file);
  if (ext === ".map") problems.push(`source map present: ${relative(outDir, file)}`);
  if (ext === ".html" || ext === ".txt") {
    const text = readFileSync(file, "utf8");
    if (/localhost|127\.0\.0\.1/.test(text)) problems.push(`local address referenced in ${relative(outDir, file)}`);
    if (text.includes("api-health")) problems.push(`development page referenced in ${relative(outDir, file)}`);
  }
}
if (problems.length > 0) fail(`Export checks failed:\n  - ${problems.join("\n  - ")}`);

const bytes = files.reduce((total, file) => total + statSync(file).size, 0);
console.log(`\n[build:static] OK: ${files.length} files (${(bytes / 1024).toFixed(0)} KB) in ${outDir}`);
console.log("[build:static] Upload the CONTENTS of this folder into your domain's htdocs folder.");
