/**
 * Regenerate `src/lib/api-types.ts` from the backend's OpenAPI schema.
 *
 * This exists because the one-liner it replaces was POSIX-only:
 *
 *   openapi-typescript ${API_SCHEMA_URL:-http://localhost:8000/openapi.json} ...
 *
 * npm runs scripts through `cmd.exe` on Windows, which has no `${VAR:-default}`
 * expansion and passes the braces through as a literal argument. The generator
 * then tried to open a file called `${API_SCHEMA_URL:-http:\localhost:8000\
 * openapi.json}` and failed with ENOENT, which reads exactly like the backend
 * refusing to serve its schema. It was not: the default had simply never been
 * applied on this platform.
 *
 * Resolving the default in Node fixes it everywhere, and the generator is
 * spawned through its own bin entry rather than a shell, so no argument is
 * reinterpreted on the way.
 */

import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import path from "node:path";

const DEFAULT_SCHEMA_URL = "http://localhost:8000/openapi.json";
const OUTPUT = "src/lib/api-types.ts";

const schemaUrl = process.env.API_SCHEMA_URL?.trim() || DEFAULT_SCHEMA_URL;

// Resolved through the package's own manifest rather than by asking for
// `openapi-typescript/bin/cli.js` directly: its `exports` map rewrites
// `./*.js` to `./*.mjs`, so the direct specifier resolves to a file that does
// not exist. The manifest is reachable (`"./*": "./*"`), and its `bin` entry
// is the package's own statement of where its CLI lives.
const require = createRequire(import.meta.url);
const manifestPath = require.resolve("openapi-typescript/package.json");
const manifest = require("openapi-typescript/package.json");
const cli = path.join(
  path.dirname(manifestPath),
  manifest.bin["openapi-typescript"],
);

console.log(`Reading the API schema from ${schemaUrl}`);

const result = spawnSync(process.execPath, [cli, schemaUrl, "-o", OUTPUT], {
  stdio: "inherit",
});

if (result.error) {
  console.error(`Could not run openapi-typescript: ${result.error.message}`);
  process.exit(1);
}
if (result.status !== 0) {
  console.error(
    `\nopenapi-typescript failed. Is the backend running and serving ${schemaUrl}?\n` +
      `Start it with: cd backend; uvicorn app.main:app --reload --port 8000`,
  );
}
process.exit(result.status ?? 1);
