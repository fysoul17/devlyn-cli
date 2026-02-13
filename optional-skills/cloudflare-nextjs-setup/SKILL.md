---
name: cloudflare-nextjs-setup
description: Set up Cloudflare Workers deployment for an existing Next.js project using OpenNext. Triggers on "deploy to Cloudflare", "set up Cloudflare Workers", "Cloudflare deployment", "add Cloudflare to this project".
argument-hint: "[project-name]"
disable-model-invocation: true
---

# Cloudflare Workers + Next.js Setup

Set up Cloudflare Workers deployment for an existing Next.js project using OpenNext.

## Procedure

Follow these 8 steps in order. Read existing files before modifying them.

### Step 1: Detect Environment

Before making any changes, gather project context:

1. **Package manager** — Check for `pnpm-lock.yaml`, `yarn.lock`, `bun.lockb`, or `package-lock.json` (in that priority order)
2. **Next.js config format** — Check for `next.config.ts`, `next.config.mjs`, or `next.config.js`
3. **Existing Cloudflare config** — Check for `wrangler.jsonc`, `wrangler.toml`, `wrangler.json`, or `open-next.config.ts`. If found, warn the user and ask before overwriting
4. **Monorepo detection** — Check if `package.json` has `workspaces` field or if a root `pnpm-workspace.yaml` exists. If monorepo, determine which directory contains the Next.js app (look for `next.config.*`)
5. **Project name** — Use `$ARGUMENTS` if provided, otherwise extract `name` from the app's `package.json`

Store results for use in subsequent steps. All config files go in the **Next.js app directory** (not the monorepo root).

### Step 2: Install Dependencies

Install using the detected package manager. Both packages go in the Next.js app directory:

- `@opennextjs/cloudflare` — as a **dependency** (required at runtime)
- `wrangler` — as a **devDependency** (CLI tooling only)

Examples:
```bash
# pnpm (with workspace filter if monorepo)
pnpm add @opennextjs/cloudflare
pnpm add -D wrangler

# npm
npm install @opennextjs/cloudflare
npm install -D wrangler

# yarn
yarn add @opennextjs/cloudflare
yarn add -D wrangler

# bun
bun add @opennextjs/cloudflare
bun add -D wrangler
```

### Step 3: Create open-next.config.ts

Create `open-next.config.ts` in the Next.js app directory with minimal config:

```ts
import { defineCloudflareConfig } from "@opennextjs/cloudflare";

export default defineCloudflareConfig({});
```

This is the minimal working config. Advanced options (R2 cache, custom bindings) can be added later.

### Step 4: Create wrangler.jsonc

Create `wrangler.jsonc` in the Next.js app directory. Use today's date for `compatibility_date` and the project name from Step 1:

```jsonc
{
  "$schema": "node_modules/wrangler/config-schema.json",
  "main": ".open-next/worker.js",
  "name": "<PROJECT_NAME>",
  "compatibility_date": "<TODAY_YYYY-MM-DD>",
  "compatibility_flags": ["nodejs_compat"],
  "assets": {
    "directory": ".open-next/assets",
    "binding": "ASSETS"
  }
  // Non-secret env vars can be added here:
  // "vars": {
  //   "EXAMPLE_VAR": "value"
  // }
  // Secrets must be set via: npx wrangler secret put <KEY_NAME>
}
```

**CRITICAL**: The `"nodejs_compat"` compatibility flag is **required**. Without it, Node.js APIs (crypto, buffer, etc.) will fail at runtime with cryptic errors.

### Step 5: Modify next.config

Add `initOpenNextCloudflareForDev()` to the **top** of the Next.js config file. This call MUST be:
- At **module level** (not inside a function, not conditional)
- **Before** any other config logic
- An **import + call** pattern, not dynamic import

Read the existing config file first, then add the import and call at the very top:

**For `.mjs` or `.js` (ESM):**
```js
import { initOpenNextCloudflareForDev } from "@opennextjs/cloudflare";

initOpenNextCloudflareForDev();

// ... rest of existing config unchanged ...
```

**For `.ts`:**
```ts
import { initOpenNextCloudflareForDev } from "@opennextjs/cloudflare";

initOpenNextCloudflareForDev();

// ... rest of existing config unchanged ...
```

**For `.js` (CommonJS — rare with modern Next.js):**
```js
const { initOpenNextCloudflareForDev } = require("@opennextjs/cloudflare");

initOpenNextCloudflareForDev();

// ... rest of existing config unchanged ...
```

**GOTCHA**: `initOpenNextCloudflareForDev()` must execute at module evaluation time. Do NOT wrap it in `if (process.env.NODE_ENV === 'development')` or any other conditional — it handles environment detection internally.

### Step 6: Add Package.json Scripts

Add these scripts to the Next.js app's `package.json`. Read the file first and merge with existing scripts — do not overwrite:

```json
{
  "scripts": {
    "build:worker": "opennextjs-cloudflare build",
    "preview": "opennextjs-cloudflare build && opennextjs-cloudflare preview",
    "deploy": "opennextjs-cloudflare build && opennextjs-cloudflare deploy"
  }
}
```

If `build:worker`, `preview`, or `deploy` scripts already exist, warn the user and ask before overwriting.

### Step 7: Update .gitignore

Add Cloudflare-specific entries to the project's `.gitignore` (either the Next.js app's or the repo root, whichever exists). Only add entries that are not already present:

```gitignore
# cloudflare
.open-next/
.dev.vars
```

- `.open-next/` — build output directory (large, regenerated on every build)
- `.dev.vars` — local secrets file (equivalent of `.env` for Wrangler)

### Step 8: Guide Secrets Setup

After all file changes are complete, check for existing `.env` / `.env.local` files and inform the user about secrets management:

1. **For local development** — Check if the project already has `.env` or `.env.local` files:
   - **If `.env` / `.env.local` already exists**: The existing file works as-is for `next dev` (via `initOpenNextCloudflareForDev()`). Do NOT ask the user to duplicate values into `.dev.vars`. Only mention that `.dev.vars` exists as an alternative if they ever run `wrangler dev` directly (outside of Next.js).
   - **If no `.env` file exists**: Create a `.dev.vars` file in the Next.js app directory with placeholder keys:
     ```
     SECRET_KEY=your-local-value
     ANOTHER_SECRET=another-value
     ```
     This file is gitignored and read by both `wrangler dev` and `next dev` (via the OpenNext dev hook).

2. **For production**, secrets must be set via the Wrangler CLI:
   ```bash
   npx wrangler secret put SECRET_KEY
   npx wrangler secret put ANOTHER_SECRET
   ```
   Each command prompts for the value interactively. Secrets are encrypted and stored by Cloudflare.

3. **Non-secret env vars** (public URLs, feature flags) go in `wrangler.jsonc` under `"vars"`:
   ```jsonc
   "vars": {
     "PUBLIC_API_URL": "https://api.example.com"
   }
   ```

4. **First deploy**: Run `npm run deploy` (or equivalent). The user will be prompted to log in to Cloudflare if not already authenticated.

5. **Cloudflare Dashboard setup** — If deploying via the Cloudflare dashboard (Workers & Pages > Create > Connect to Git), inform the user to configure these fields correctly:
   - **Project name**: Must match the `"name"` field in `wrangler.jsonc` (e.g., `pyx-interface-v1`). A mismatch creates a separate worker and causes deployment conflicts.
   - **Build command**: Must be the **OpenNext build**, not the default Next.js build. Use the package manager detected in Step 1:
     - pnpm: `pnpm run build:worker`
     - npm: `npm run build:worker`
     - yarn: `yarn build:worker`
     - bun: `bun run build:worker`
     - Or directly: `npx opennextjs-cloudflare build`
   - **Deploy command**: `npx wrangler deploy` (the dashboard default is correct)

   **CRITICAL**: The default build command pre-filled by Cloudflare (e.g., `pnpm run build`) runs `next build` only — it does **not** run the OpenNext build step that produces the `.open-next/` output. The deploy will fail or serve a broken app if the build command is not changed to `build:worker`.

6. **Production secrets** — After the first deploy, set all secret environment variables via the Wrangler CLI. Scan the project for env vars (check `.env`, `.env.local`, `.dev.vars`, and any `process.env.*` references in the codebase) and instruct the user to run `npx wrangler secret put <KEY>` for each one:
   ```bash
   npx wrangler secret put SECRET_KEY
   npx wrangler secret put ANOTHER_SECRET
   # Repeat for each secret env var the project uses
   ```
   Each command prompts for the value interactively. Secrets are encrypted and stored by Cloudflare, never committed to source.

   Alternatively, secrets can be set in the Cloudflare dashboard: **Workers & Pages > your project > Settings > Variables and Secrets > Add**.

   **IMPORTANT**: The worker will fail at runtime if required env vars are not set. Always list the specific env var names the project needs so the user knows exactly what to configure.

## Gotchas & Troubleshooting

### "X is not a function" or Node.js API errors at runtime
**Cause**: Missing `nodejs_compat` compatibility flag.
**Fix**: Ensure `wrangler.jsonc` includes `"compatibility_flags": ["nodejs_compat"]`.

### Config files in wrong directory (monorepo)
**Cause**: `wrangler.jsonc` and `open-next.config.ts` placed in the monorepo root instead of the Next.js app directory.
**Fix**: Move all Cloudflare config files to the directory containing `next.config.*`.

### Environment variables are undefined in production
**Cause**: Secrets not set via `wrangler secret put`.
**Fix**: Run `npx wrangler secret put <KEY_NAME>` for each secret. Non-secret vars go in `wrangler.jsonc` `"vars"`.

### `initOpenNextCloudflareForDev()` not working
**Cause**: Wrapped in a conditional or placed inside a function.
**Fix**: Must be called at module top-level, unconditionally, before any config exports.

### Build succeeds but deploy fails with "no routes"
**Cause**: `"main"` or `"assets.directory"` paths in `wrangler.jsonc` don't match the OpenNext output.
**Fix**: Ensure `"main": ".open-next/worker.js"` and `"assets": { "directory": ".open-next/assets" }`.

### `wrangler dev` doesn't pick up `.dev.vars`
**Cause**: File is in the wrong directory or has wrong filename.
**Fix**: `.dev.vars` must be in the same directory as `wrangler.jsonc` (the Next.js app directory).

## Advanced Configuration

### R2 Cache (ISR/Incremental Static Regeneration)

To enable ISR with R2 storage, update `open-next.config.ts`:

```ts
import { defineCloudflareConfig } from "@opennextjs/cloudflare";
import r2IncrementalCache from "@opennextjs/cloudflare/overrides/incremental-cache/r2-incremental-cache";

export default defineCloudflareConfig({
  incrementalCache: r2IncrementalCache,
});
```

And add the R2 binding to `wrangler.jsonc`:

```jsonc
{
  "r2_buckets": [
    {
      "binding": "NEXT_INC_CACHE_R2_BUCKET",
      "bucket_name": "<your-bucket-name>"
    }
  ]
}
```

### Cloudflare Bindings (KV, D1, etc.)

Add bindings directly to `wrangler.jsonc`. They are accessible in Next.js via `getCloudflareContext()`:

```ts
import { getCloudflareContext } from "@opennextjs/cloudflare";

export async function GET() {
  const { env } = await getCloudflareContext();
  const value = await env.MY_KV.get("key");
  return Response.json({ value });
}
```

```jsonc
// wrangler.jsonc
{
  "kv_namespaces": [
    { "binding": "MY_KV", "id": "<namespace-id>" }
  ]
}
```
